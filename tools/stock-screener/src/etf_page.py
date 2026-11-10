"""普通静态网页。不是录屏用的 9:16 HTML。"""

from __future__ import annotations

import json
from pathlib import Path

import pandas as pd



def _flow_chart(group: dict) -> dict:
    series = group["anomaly"]
    rule = group["anomaly_rule"]
    total = int(rule["total"])
    each = int(rule["each"])
    sync_n = int(rule["sync"])
    index_name = group["index_name"]
    counter = [point for point in series if point["kind"] == "counter"]
    syncup = [point for point in series if point["kind"] == "syncup"]
    sell = [point for point in series if point["kind"] == "sell"]
    venue = {"star50": "上交所", "chinext": "深交所"}.get(group["id"], "上交所、深交所")
    return {
        "points": series,
        "index": index_name,
        "each": each,
        "title": f"周净申购：当周头部 ETF 在{venue}公布的份额，本周末减去上周末。头部按当周持有规模重选",
        "axis": (
            f"纵坐标：左轴是{index_name}收盘点位，通达信不复权。"
            f"右轴是合计周净申购，单位亿份。深红和橙色是合计至少 {total} 亿份且至少 {sync_n} 只各超过 {each} 亿份。"
            f"绿柱是合计净赎回至少 {total} 亿份。"
        ),
        "note": (
            f"深红柱是{index_name}当周下跌、合计净申购至少 {total} 亿份，且至少 {sync_n} 只各超过 {each} 亿份，共 {len(counter)} 周。"
            f"橙柱是同样的规模，但指数当周收涨，共 {len(syncup)} 周。"
            f"绿柱是合计净赎回至少 {total} 亿份，共 {len(sell)} 周。"
            "浅蓝柱是指数上涨、又没有这么多只一起放量的申购。"
        ),
    }


def _panels(groups: list[dict]) -> list[dict]:
    panels = []
    for group in groups:
        weekly = group["weekly"]
        last = weekly.iloc[-1]
        panels.append(
            {
                "label": group["label"],
                "market": group["market_name"],
                "index": group["index_name"],
                "last_share": round(float(last["share_pct"]), 2),
                "last_aum_yi": round(float(last["aum"]) / 1e8, 0),
                "last_cap_yi": round(float(last["market_cap"]) / 1e8, 0),
                "span": f"{float(weekly['share_pct'].min()):.2f}%–{float(weekly['share_pct'].max()):.2f}%",
                "flow": group["flow"]["text"],
                "members": group["members"],
                "flowChart": _flow_chart(group),
                "points": [
                    {
                        "date": pd.Timestamp(row.date).strftime("%Y-%m-%d"),
                        "open": round(float(row.open), 2),
                        "high": round(float(row.high), 2),
                        "low": round(float(row.low), 2),
                        "close": round(float(row.close), 2),
                        "share": None if pd.isna(row.share_pct) else round(float(row.share_pct), 3),
                        "lots": round(float(row.shares) / 1e8, 2),
                        "aum": None if pd.isna(row.aum) else round(float(row.aum) / 1e8, 1),
                        "cap": None if pd.isna(row.market_cap) else round(float(row.market_cap) / 1e8, 0),
                    }
                    for row in weekly.itertuples(index=False)
                ],
            }
        )
    return panels


def _anomaly(groups: list[dict]) -> dict:
    series = next(group["anomaly"] for group in groups if group["id"] == "csi300")
    counter = [point for point in series if point["kind"] == "counter"]
    latest = counter[-3:]
    latest_text = "、".join(
        f"{point['date']}（{point['total']:+.0f} 亿份，指数 {point['ret']:+.1f}%）" for point in latest
    )
    syncup = [point for point in series if point["kind"] == "syncup"]
    sync_text = "、".join(
        f"{point['date']}（{point['total']:+.0f} 亿份，指数 {point['ret']:+.1f}%）" for point in syncup[-2:]
    )
    sell = [point for point in series if point["kind"] == "sell"]
    sell_text = "、".join(
        f"{point['date']}（{point['total']:+.0f} 亿份，指数 {point['ret']:+.1f}%）" for point in sell[-2:]
    )
    note = (
        f"深红柱是沪深300当周下跌、四只合计净申购至少 40 亿份，且至少三只各超过 5 亿份，共 {len(counter)} 周。"
        f"最近三次：{latest_text}。"
        f"橙柱同样是多只一起大额申购，但指数当周收涨，共 {len(syncup)} 周，最近：{sync_text}。"
        f"绿柱是四只合计净赎回至少 40 亿份，共 {len(sell)} 周"
        + (f"，最近：{sell_text}。" if sell else "。")
        + "浅蓝柱是指数上涨、又没有三只以上一起放量的申购，更接近散户追涨。"
        "份额看不出账户，不能据此认定就是汇金。"
    )
    return {"points": series, "note": note}


def write_page(groups: list[dict], path: Path) -> None:
    asof = pd.Timestamp(groups[0]["asof"]).strftime("%Y-%m-%d")
    payload = {"panels": _panels(groups)}
    data = json.dumps(payload, ensure_ascii=False).replace("<", "<")
    html = _PAGE.replace("__ASOF__", asof).replace("__DATA__", data)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(html, encoding="utf-8")


_PAGE = r"""<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>头部 ETF 持有规模占板块总市值</title>
<style>
  body { margin: 0; background: #f3f4f6; color: #1a1a1a; font-family: "Microsoft YaHei", "PingFang SC", sans-serif; }
  main { max-width: 1080px; margin: 0 auto; padding: 32px 20px 56px; }
  h1 { font-size: 26px; line-height: 1.3; margin: 0 0 8px; }
  .lead { margin: 0; color: #4b4b4b; font-size: 14px; line-height: 1.7; }
  section { background: #fff; border: 1px solid #e3e3e3; margin-top: 18px; padding: 16px 16px 8px; }
  h2 { font-size: 18px; margin: 0 0 4px; }
  h3 { font-size: 15px; line-height: 1.45; margin: 16px 0 2px; }
  .axis { margin: 0 0 6px; color: #444; font-size: 13px; line-height: 1.55; }
  .meta { margin: 0; color: #333; font-size: 13px; line-height: 1.6; }
  ul { display: flex; flex-wrap: wrap; gap: 6px 18px; padding: 0; margin: 10px 0 4px; list-style: none; font-size: 13px; }
  .chart { position: relative; }
  canvas { width: 100%; height: 340px; display: block; cursor: crosshair; }
  .brush canvas { height: 72px; cursor: ew-resize; }
  .tip { min-height: 20px; margin: 2px 0 8px; color: #333; font-size: 12px; }
  footer { margin-top: 16px; color: #666; font-size: 12px; line-height: 1.7; }
</style>
</head>
<body>
<main>
  <h1>头部 ETF 持有规模占板块总市值</h1>
  <p class="lead">截至 __ASOF__。每组三张图。头部按当周持有规模重选，留下达到最大那只 10% 以上的，最多 4 只，名单会变。每张图下方色带可以拖动，拖两端改显示区间。</p>
  <div id="boards"></div>
  <footer>
    持有规模 = 基金份额 × 当日收盘价。份额来自上交所、深交所公布的 ETF 份额；收盘价来自本机通达信，基金价格按三位小数还原。
    总市值来自交易所每日股票概况：沪深300 用沪市主板 A + 科创板 + 深市主板 A + 创业板，科创50 用科创板，创业板用创业板。不含 B 股和北交所。
    周占比用当周最后一个交易日的份额和总市值。份额图只计当周入选头部的基金份额，价格涨跌不算申购。申购异动只计当周头部各自相对上周末的份额变化，新上市的整周份额不计入。仅供参考。
  </footer>
</main>
<script>
const pack = __DATA__;
const panels = pack.panels;
const flowPaints = [];
const seriesPaints = [];
const root = document.getElementById("boards");
panels.forEach((panel, index) => {
  const section = document.createElement("section");
  const funds = panel.members.map((item) => `${item.code} ${item.name} ${item.aum_yi} 亿 / ${item.shares_yi} 亿份`).join(" · ");
  const universe = panel.market === "全A" ? "沪市主板A + 科创板 + 深市主板A + 创业板" : panel.market;
  section.innerHTML = `<h2>${panel.label}</h2>
    <p class="meta">${panel.members.length} 只 · 最新一周持有 ${panel.last_aum_yi} 亿，占${panel.market}总市值 ${panel.last_share}%（板块 ${panel.last_cap_yi} 亿）· 区间 ${panel.span}</p>
    <p class="meta">${panel.flow}</p>
    <ul><li>${funds}</li></ul>
    <h3>持有规模占${panel.market}总市值：当周头部的交易所基金份额 × 通达信收盘价，除以交易所股票概况里的${universe}总市值。头部按当周持有规模重选</h3>
    <p class="axis">纵坐标：左轴是${panel.index}收盘点位，通达信不复权。右轴是持有规模占${panel.market}总市值。两个数都取当周最后一个交易日。</p>
    <div class="chart"><canvas id="c${index}"></canvas></div>
    <div class="brush"><canvas id="cb${index}"></canvas></div>
    <p class="axis" id="cr${index}"></p>
    <div class="tip" id="t${index}">鼠标移到图上看点位和占比</div>
    <h3>基金份额：当周头部 ETF 的交易所份额相加。头部按当周持有规模重选</h3>
    <p class="axis">纵坐标：左轴是${panel.index}收盘点位，通达信不复权。右轴是合计份额，单位亿份。取当周最后一个交易日。</p>
    <div class="chart"><canvas id="f${index}"></canvas></div>
    <div class="brush"><canvas id="fb${index}"></canvas></div>
    <p class="axis" id="fr${index}"></p>
    <div class="tip" id="u${index}">鼠标移到图上看份额</div>
    ${panel.flowChart ? `<h3>${panel.flowChart.title}</h3>
    <p class="axis">${panel.flowChart.axis}</p>
    <p class="meta">${panel.flowChart.note}</p>
    <div class="chart"><canvas id="a${index}"></canvas></div>
    <div class="brush"><canvas id="b${index}"></canvas></div>
    <p class="axis" id="r${index}"></p>
    <div class="tip" id="v${index}">深红是逆势同步买入，橙色是上涨但仍多只同步，绿色是大额赎回，浅蓝是上涨且未同步，灰色是其余周</div>`
    : `<h3>成交额占${panel.market}：通达信里这几只 ETF 的当周成交额合计，除以${universe}股票的当周成交额</h3>
    <p class="axis">纵坐标：左轴是${panel.index}收盘点位，通达信不复权。右轴是成交额占比。分子和分母都按该周每个交易日相加。</p>
    <div class="chart"><canvas id="a${index}"></canvas></div>
    <div class="tip" id="v${index}">鼠标移到图上看当周成交额</div>`}`;
  root.appendChild(section);
  mountSeries("c" + index, "cb" + index, "cr" + index, "t" + index, panel, "share", "占" + panel.market + "总市值", "share", "pct", panel.points.filter((p) => p.share != null));
  mountSeries("f" + index, "fb" + index, "fr" + index, "u" + index, panel, "lots", "份额（亿份）", "lots", "lots", panel.points);
  if (panel.flowChart) {
    mountFlow("a" + index, "b" + index, "r" + index, "v" + index, panel.flowChart);
  } else {
    const turn = document.getElementById("a" + index);
    const turnPoints = panel.points.filter((p) => p.turn != null);
    draw(turn, turnPoints, panel.index, "占" + panel.market + "成交额", "turn", "pct");
    bind(turn, document.getElementById("v" + index), panel, "turn", turnPoints);
  }
});

function draw(canvas, points, indexName, rightName, rightKey, rightKind) {
  const dpr = window.devicePixelRatio || 1;
  const width = canvas.clientWidth;
  const height = canvas.clientHeight;
  canvas.width = Math.max(1, Math.floor(width * dpr));
  canvas.height = Math.max(1, Math.floor(height * dpr));
  const ctx = canvas.getContext("2d");
  ctx.setTransform(dpr, 0, 0, dpr, 0, 0);
  const pad = {l: 62, r: 56, t: 18, b: 32};
  const plotW = width - pad.l - pad.r;
  const plotH = height - pad.t - pad.b;
  const n = points.length;
  const pmin = Math.min(...points.map((p) => p.low));
  const pmax = Math.max(...points.map((p) => p.high));
  const smax = Math.max(...points.map((p) => p[rightKey])) * 1.12;
  const x = (i) => pad.l + (n < 2 ? plotW / 2 : (i / (n - 1)) * plotW);
  const yPrice = (v) => pad.t + (pmax - v) / (pmax - pmin || 1) * plotH;
  const yShare = (v) => pad.t + (smax - v) / (smax || 1) * plotH;
  ctx.clearRect(0, 0, width, height);
  ctx.strokeStyle = "#ececec";
  ctx.lineWidth = 1;
  ctx.font = "12px Microsoft YaHei, sans-serif";
  ctx.fillStyle = "#666";
  for (let k = 0; k < 4; k++) {
    const y = pad.t + (plotH * k) / 3;
    ctx.beginPath();
    ctx.moveTo(pad.l, y);
    ctx.lineTo(width - pad.r, y);
    ctx.stroke();
    const price = pmax - (pmax - pmin) * k / 3;
    const share = smax - smax * k / 3;
    ctx.textAlign = "right";
    ctx.fillText(price.toFixed(0), pad.l - 8, y + 4);
    ctx.textAlign = "left";
    ctx.fillStyle = "#1d4e89";
    const rightText = rightKind === "pct" ? share.toFixed(2) + "%" : share.toFixed(0);
    ctx.fillText(rightText, width - pad.r + 8, y + 4);
    ctx.fillStyle = "#666";
  }
  const body = Math.max(2, plotW / n * 0.62);
  points.forEach((p, i) => {
    const up = p.close >= p.open;
    const color = up ? "#d84a4a" : "#1c9a62";
    const cx = x(i);
    ctx.strokeStyle = color;
    ctx.beginPath();
    ctx.moveTo(cx, yPrice(p.high));
    ctx.lineTo(cx, yPrice(p.low));
    ctx.stroke();
    const top = yPrice(Math.max(p.open, p.close));
    const bot = yPrice(Math.min(p.open, p.close));
    ctx.fillStyle = color;
    ctx.fillRect(cx - body / 2, top, body, Math.max(1, bot - top));
  });
  ctx.beginPath();
  ctx.strokeStyle = "#1d4e89";
  ctx.lineWidth = 1.7;
  points.forEach((p, i) => {
    const cx = x(i);
    const cy = yShare(p[rightKey]);
    if (i === 0) ctx.moveTo(cx, cy);
    else ctx.lineTo(cx, cy);
  });
  ctx.stroke();
  ctx.fillStyle = "#888";
  ctx.textAlign = "center";
  const step = Math.max(1, Math.round(n / 6));
  for (let i = 0; i < n; i += step) {
    ctx.fillText(points[i].date.slice(0, 7), x(i), height - 10);
  }
  ctx.textAlign = "left";
  ctx.fillStyle = "#666";
  ctx.fillText("左轴 " + indexName + "（点）", pad.l, 12);
  ctx.fillStyle = "#1d4e89";
  ctx.textAlign = "right";
  ctx.fillText("右轴 " + rightName, width - pad.r, 12);
  canvas._geom = {pad, plotW, n, x};
}

function bind(canvas, tip, panel, mode, rows) {
  const current = () => (typeof rows === "function" ? rows() : (rows || panel.points));
  canvas.addEventListener("mousemove", (event) => {
    const geom = canvas._geom;
    const points = current();
    if (!geom || !points.length) return;
    const rect = canvas.getBoundingClientRect();
    const px = event.clientX - rect.left;
    let nearest = 0;
    let best = Infinity;
    points.forEach((_, i) => {
      const dist = Math.abs(geom.x(i) - px);
      if (dist < best) { best = dist; nearest = i; }
    });
    const p = points[nearest];
    if (mode === "lots") {
      tip.textContent = `${p.date}  ${panel.index} ${p.close.toFixed(2)}  份额 ${p.lots.toFixed(1)} 亿份`;
    } else if (mode === "turn") {
      tip.textContent = `${p.date}  ${panel.index} ${p.close.toFixed(2)}  成交额 ${p.etf_amt} 亿 / ${panel.market} ${p.board_amt} 亿  占比 ${p.turn.toFixed(2)}%`;
    } else {
      tip.textContent = `${p.date}  ${panel.index} ${p.close.toFixed(2)}  持有 ${p.aum} 亿 / ${panel.market} ${p.cap} 亿  占比 ${p.share.toFixed(2)}%`;
    }
  });
}


function drawAnomaly(canvas, points, indexName) {
  const dpr = window.devicePixelRatio || 1;
  const width = canvas.clientWidth;
  const height = canvas.clientHeight;
  canvas.width = Math.max(1, Math.floor(width * dpr));
  canvas.height = Math.max(1, Math.floor(height * dpr));
  const ctx = canvas.getContext("2d");
  ctx.setTransform(dpr, 0, 0, dpr, 0, 0);
  const pad = {l: 62, r: 64, t: 18, b: 32};
  const plotW = width - pad.l - pad.r;
  const plotH = height - pad.t - pad.b;
  const n = points.length;
  const pmin = Math.min(...points.map((p) => p.close));
  const pmax = Math.max(...points.map((p) => p.close));
  const totals = points.map((p) => p.total);
  const bmin = Math.min(0, ...totals);
  const bmax = Math.max(0, ...totals);
  const bpad = (bmax - bmin) * 0.12 || 1;
  const x = (i) => pad.l + (n < 2 ? plotW / 2 : (i / (n - 1)) * plotW);
  const yPrice = (v) => pad.t + (pmax - v) / (pmax - pmin || 1) * plotH;
  const yBar = (v) => pad.t + (bmax + bpad - v) / (bmax - bmin + 2 * bpad) * plotH;
  ctx.clearRect(0, 0, width, height);
  ctx.strokeStyle = "#ececec";
  ctx.beginPath();
  ctx.moveTo(pad.l, yBar(0));
  ctx.lineTo(width - pad.r, yBar(0));
  ctx.stroke();
  const body = Math.max(2, plotW / n * 0.72);
  const colorOf = {counter: "#9d1c3d", syncup: "#d06a1f", sell: "#1c9a62", chase: "#7ea0c8", other: "#c8c8c8"};
  points.forEach((p, i) => {
    const cx = x(i);
    const y0 = yBar(0);
    const y1 = yBar(p.total);
    ctx.fillStyle = colorOf[p.kind] || "#c8c8c8";
    ctx.fillRect(cx - body / 2, Math.min(y0, y1), body, Math.max(1, Math.abs(y1 - y0)));
  });
  ctx.beginPath();
  ctx.strokeStyle = "#222";
  ctx.lineWidth = 1.4;
  points.forEach((p, i) => {
    const cx = x(i);
    const cy = yPrice(p.close);
    if (i === 0) ctx.moveTo(cx, cy);
    else ctx.lineTo(cx, cy);
  });
  ctx.stroke();
  ctx.font = "12px Microsoft YaHei, sans-serif";
  ctx.fillStyle = "#666";
  ctx.textAlign = "right";
  ctx.fillText(pmax.toFixed(0), pad.l - 8, pad.t + 4);
  ctx.fillText(pmin.toFixed(0), pad.l - 8, pad.t + plotH);
  ctx.textAlign = "left";
  ctx.fillStyle = "#9d1c3d";
  ctx.fillText(bmax.toFixed(0), width - pad.r + 8, yBar(bmax) + 4);
  ctx.fillText(bmin.toFixed(0), width - pad.r + 8, yBar(bmin));
  ctx.fillStyle = "#888";
  ctx.textAlign = "center";
  const step = Math.max(1, Math.round(n / 6));
  for (let i = 0; i < n; i += step) ctx.fillText(points[i].date.slice(0, 7), x(i), height - 10);
  ctx.textAlign = "left";
  ctx.fillStyle = "#222";
  ctx.fillText("左轴 " + (indexName || "沪深300") + "（点）", pad.l, 12);
  ctx.fillStyle = "#9d1c3d";
  ctx.textAlign = "right";
  ctx.fillText("右轴 周净申购（亿份）", width - pad.r, 12);
  canvas._geom = {n, x};
}
function bindAnomaly(canvas, tip) {
  canvas.addEventListener("mousemove", (event) => {
    const geom = canvas._geom;
    const points = anomalySlice();
    if (!geom || !points.length) return;
    const px = event.clientX - canvas.getBoundingClientRect().left;
    let nearest = 0;
    let best = Infinity;
    points.forEach((_, i) => {
      const dist = Math.abs(geom.x(i) - px);
      if (dist < best) { best = dist; nearest = i; }
    });
    const p = points[nearest];
    const label = p.kind === "counter" ? "逆势同步" : (p.kind === "syncup" ? "上涨仍同步" : (p.kind === "sell" ? "卖出同步" : (p.kind === "chase" ? "上涨未同步" : "其余")));
    tip.textContent = `${p.date}  沪深300 ${p.close.toFixed(0)}（${p.ret > 0 ? "+" : ""}${p.ret.toFixed(1)}%）  净申购 ${p.total > 0 ? "+" : ""}${p.total.toFixed(0)} 亿份  ${p.sync} 只超过 5 亿份  ${label}`;
  });
}

function drawAnomalyBrush(canvas, points, range) {
  const dpr = window.devicePixelRatio || 1;
  const width = canvas.clientWidth;
  const height = canvas.clientHeight;
  canvas.width = Math.max(1, Math.floor(width * dpr));
  canvas.height = Math.max(1, Math.floor(height * dpr));
  const ctx = canvas.getContext("2d");
  ctx.setTransform(dpr, 0, 0, dpr, 0, 0);
  const pad = {l: 62, r: 64, t: 6, b: 18};
  const plotW = width - pad.l - pad.r;
  const plotH = height - pad.t - pad.b;
  const n = points.length;
  const totals = points.map((p) => p.total);
  const bmin = Math.min(0, ...totals);
  const bmax = Math.max(0, ...totals);
  const x = (i) => pad.l + (n < 2 ? plotW / 2 : (i / (n - 1)) * plotW);
  const yBar = (v) => pad.t + (bmax - v) / (bmax - bmin || 1) * plotH;
  ctx.clearRect(0, 0, width, height);
  ctx.strokeStyle = "#ececec";
  ctx.beginPath();
  ctx.moveTo(pad.l, yBar(0));
  ctx.lineTo(width - pad.r, yBar(0));
  ctx.stroke();
  const body = Math.max(1, plotW / n);
  const colorOf = {counter: "#9d1c3d", syncup: "#d06a1f", sell: "#1c9a62", chase: "#7ea0c8", other: "#d0d0d0"};
  points.forEach((p, i) => {
    const cx = x(i);
    const y0 = yBar(0);
    const y1 = yBar(p.total);
    ctx.fillStyle = colorOf[p.kind] || "#d0d0d0";
    ctx.fillRect(cx - body / 2, Math.min(y0, y1), Math.max(1, body), Math.max(1, Math.abs(y1 - y0)));
  });
  const x0 = x(range.start);
  const x1 = x(range.end);
  ctx.fillStyle = "rgba(29, 78, 137, 0.16)";
  ctx.fillRect(x0, pad.t, Math.max(2, x1 - x0), plotH);
  ctx.strokeStyle = "#1d4e89";
  ctx.lineWidth = 1.5;
  ctx.strokeRect(x0, pad.t, Math.max(2, x1 - x0), plotH);
  ctx.fillStyle = "#1d4e89";
  ctx.fillRect(x0 - 2, pad.t, 4, plotH);
  ctx.fillRect(x1 - 2, pad.t, 4, plotH);
  ctx.font = "11px Microsoft YaHei, sans-serif";
  ctx.fillStyle = "#666";
  ctx.textAlign = "left";
  ctx.fillText(points[0].date.slice(0, 7), pad.l, height - 4);
  ctx.textAlign = "right";
  ctx.fillText(points[n - 1].date.slice(0, 7), width - pad.r, height - 4);
  canvas._geom = {n, x, pad};
}
function bindBrush(canvas) {
  let drag = null;
  const indexAt = (event) => {
    const geom = canvas._geom;
    const px = event.clientX - canvas.getBoundingClientRect().left;
    let nearest = 0;
    let best = Infinity;
    for (let i = 0; i < geom.n; i++) {
      const dist = Math.abs(geom.x(i) - px);
      if (dist < best) { best = dist; nearest = i; }
    }
    return nearest;
  };
  const clampRange = (start, end) => {
    const span = Math.max(8, end - start);
    let left = start;
    let right = start + span;
    if (right > anomalyAll.length - 1) {
      right = anomalyAll.length - 1;
      left = Math.max(0, right - span);
    }
    if (left < 0) {
      right -= left;
      left = 0;
    }
    anomalyRange = {start: left, end: right};
  };
  canvas.addEventListener("pointerdown", (event) => {
    if (!canvas._geom) return;
    const px = event.clientX - canvas.getBoundingClientRect().left;
    const x0 = canvas._geom.x(anomalyRange.start);
    const x1 = canvas._geom.x(anomalyRange.end);
    const i = indexAt(event);
    let mode = "move";
    if (Math.abs(px - x0) <= 8) mode = "start";
    else if (Math.abs(px - x1) <= 8) mode = "end";
    else if (px < x0 || px > x1) mode = "new";
    drag = {mode, anchor: i, start: anomalyRange.start, end: anomalyRange.end};
    canvas.setPointerCapture(event.pointerId);
  });
  canvas.addEventListener("pointermove", (event) => {
    if (!drag) return;
    const i = indexAt(event);
    if (drag.mode === "start") {
      anomalyRange.start = Math.max(0, Math.min(i, anomalyRange.end - 8));
    } else if (drag.mode === "end") {
      anomalyRange.end = Math.min(anomalyAll.length - 1, Math.max(i, anomalyRange.start + 8));
    } else if (drag.mode === "move") {
      const span = drag.end - drag.start;
      clampRange(drag.start + (i - drag.anchor), drag.start + (i - drag.anchor) + span);
    } else {
      clampRange(Math.min(drag.anchor, i), Math.max(drag.anchor, i));
    }
    paintAnomaly();
  });
  const stop = () => { drag = null; };
  canvas.addEventListener("pointerup", stop);
  canvas.addEventListener("pointercancel", stop);
}


function mountFlow(chartId, brushId, rangeId, tipId, chart) {
  const all = chart.points;
  const state = {range: {start: 0, end: Math.max(0, all.length - 1)}};
  const slice = () => all.slice(state.range.start, state.range.end + 1);
  function paint() {
    const points = slice();
    drawAnomaly(document.getElementById(chartId), points, chart.index);
    drawAnomalyBrush(document.getElementById(brushId), all, state.range);
    const label = document.getElementById(rangeId);
    if (points.length) {
      label.textContent = "显示 " + points[0].date + " 至 " + points[points.length - 1].date + "，共 " + points.length + " 周。在下方色带上拖动选区，拖两端改范围。";
    }
  }
  paint();
  bindFlowTip(document.getElementById(chartId), document.getElementById(tipId), slice, chart.index, chart.each);
  bindFlowBrush(document.getElementById(brushId), all, state, paint);
  flowPaints.push(paint);
}
function bindFlowTip(canvas, tip, getPoints, indexName, each) {
  canvas.addEventListener("mousemove", (event) => {
    const geom = canvas._geom;
    const points = getPoints();
    if (!geom || !points.length) return;
    const px = event.clientX - canvas.getBoundingClientRect().left;
    let nearest = 0;
    let best = Infinity;
    points.forEach((_, i) => {
      const dist = Math.abs(geom.x(i) - px);
      if (dist < best) { best = dist; nearest = i; }
    });
    const p = points[nearest];
    const label = p.kind === "counter" ? "逆势同步" : (p.kind === "syncup" ? "上涨仍同步" : (p.kind === "sell" ? "卖出" : (p.kind === "chase" ? "上涨未同步" : "其余")));
    tip.textContent = `${p.date}  ${indexName} ${p.close.toFixed(0)}（${p.ret > 0 ? "+" : ""}${p.ret.toFixed(1)}%）  净申购 ${p.total > 0 ? "+" : ""}${p.total.toFixed(0)} 亿份  ${p.sync} 只超过 ${each} 亿份  ${label}`;
  });
}
function bindFlowBrush(canvas, all, state, paint) {
  let drag = null;
  const indexAt = (event) => {
    const geom = canvas._geom;
    const px = event.clientX - canvas.getBoundingClientRect().left;
    let nearest = 0;
    let best = Infinity;
    for (let i = 0; i < geom.n; i++) {
      const dist = Math.abs(geom.x(i) - px);
      if (dist < best) { best = dist; nearest = i; }
    }
    return nearest;
  };
  const clampRange = (start, end) => {
    const span = Math.max(8, end - start);
    let left = start;
    let right = start + span;
    if (right > all.length - 1) {
      right = all.length - 1;
      left = Math.max(0, right - span);
    }
    if (left < 0) {
      right -= left;
      left = 0;
    }
    state.range = {start: left, end: right};
  };
  canvas.addEventListener("pointerdown", (event) => {
    if (!canvas._geom) return;
    const px = event.clientX - canvas.getBoundingClientRect().left;
    const x0 = canvas._geom.x(state.range.start);
    const x1 = canvas._geom.x(state.range.end);
    const i = indexAt(event);
    let mode = "move";
    if (Math.abs(px - x0) <= 8) mode = "start";
    else if (Math.abs(px - x1) <= 8) mode = "end";
    else if (px < x0 || px > x1) mode = "new";
    drag = {mode, anchor: i, start: state.range.start, end: state.range.end};
    canvas.setPointerCapture(event.pointerId);
  });
  canvas.addEventListener("pointermove", (event) => {
    if (!drag) return;
    const i = indexAt(event);
    if (drag.mode === "start") {
      state.range.start = Math.max(0, Math.min(i, state.range.end - 8));
    } else if (drag.mode === "end") {
      state.range.end = Math.min(all.length - 1, Math.max(i, state.range.start + 8));
    } else if (drag.mode === "move") {
      const span = drag.end - drag.start;
      clampRange(drag.start + (i - drag.anchor), drag.start + (i - drag.anchor) + span);
    } else {
      clampRange(Math.min(drag.anchor, i), Math.max(drag.anchor, i));
    }
    paint();
  });
  const stop = () => { drag = null; };
  canvas.addEventListener("pointerup", stop);
  canvas.addEventListener("pointercancel", stop);
}


function drawLineBrush(canvas, points, range, key) {
  const dpr = window.devicePixelRatio || 1;
  const width = canvas.clientWidth;
  const height = canvas.clientHeight;
  canvas.width = Math.max(1, Math.floor(width * dpr));
  canvas.height = Math.max(1, Math.floor(height * dpr));
  const ctx = canvas.getContext("2d");
  ctx.setTransform(dpr, 0, 0, dpr, 0, 0);
  const pad = {l: 62, r: 56, t: 6, b: 18};
  const plotW = width - pad.l - pad.r;
  const plotH = height - pad.t - pad.b;
  const n = points.length;
  const values = points.map((p) => p[key]);
  const vmin = Math.min(...values);
  const vmax = Math.max(...values);
  const x = (i) => pad.l + (n < 2 ? plotW / 2 : (i / (n - 1)) * plotW);
  const y = (v) => pad.t + (vmax - v) / (vmax - vmin || 1) * plotH;
  ctx.clearRect(0, 0, width, height);
  ctx.beginPath();
  ctx.strokeStyle = "#1d4e89";
  ctx.lineWidth = 1.2;
  points.forEach((p, i) => {
    const cx = x(i);
    const cy = y(p[key]);
    if (i === 0) ctx.moveTo(cx, cy);
    else ctx.lineTo(cx, cy);
  });
  ctx.stroke();
  const x0 = x(range.start);
  const x1 = x(range.end);
  ctx.fillStyle = "rgba(29, 78, 137, 0.16)";
  ctx.fillRect(x0, pad.t, Math.max(2, x1 - x0), plotH);
  ctx.strokeStyle = "#1d4e89";
  ctx.lineWidth = 1.5;
  ctx.strokeRect(x0, pad.t, Math.max(2, x1 - x0), plotH);
  ctx.fillStyle = "#1d4e89";
  ctx.fillRect(x0 - 2, pad.t, 4, plotH);
  ctx.fillRect(x1 - 2, pad.t, 4, plotH);
  ctx.font = "11px Microsoft YaHei, sans-serif";
  ctx.fillStyle = "#666";
  ctx.textAlign = "left";
  ctx.fillText(points[0].date.slice(0, 7), pad.l, height - 4);
  ctx.textAlign = "right";
  ctx.fillText(points[n - 1].date.slice(0, 7), width - pad.r, height - 4);
  canvas._geom = {n, x, pad};
}
function mountSeries(chartId, brushId, rangeId, tipId, panel, mode, rightName, rightKey, rightKind, points) {
  const all = points;
  const state = {range: {start: 0, end: Math.max(0, all.length - 1)}};
  const slice = () => all.slice(state.range.start, state.range.end + 1);
  function paint() {
    const rows = slice();
    draw(document.getElementById(chartId), rows, panel.index, rightName, rightKey, rightKind);
    drawLineBrush(document.getElementById(brushId), all, state.range, rightKey);
    const label = document.getElementById(rangeId);
    if (rows.length) {
      label.textContent = "显示 " + rows[0].date + " 至 " + rows[rows.length - 1].date + "，共 " + rows.length + " 周。在下方色带上拖动选区，拖两端改范围。";
    }
  }
  paint();
  bind(document.getElementById(chartId), document.getElementById(tipId), panel, mode, slice);
  bindFlowBrush(document.getElementById(brushId), all, state, paint);
  seriesPaints.push(paint);
}
window.addEventListener("resize", () => {
  seriesPaints.forEach((paint) => paint());
  flowPaints.forEach((paint) => paint());
});
</script>
</body>
</html>
"""
