"""普通静态网页。不是录屏用的 9:16 HTML。"""

from __future__ import annotations

import json
from pathlib import Path

import pandas as pd


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
                "points": [
                    {
                        "date": pd.Timestamp(row.date).strftime("%Y-%m-%d"),
                        "open": round(float(row.open), 2),
                        "high": round(float(row.high), 2),
                        "low": round(float(row.low), 2),
                        "close": round(float(row.close), 2),
                        "share": round(float(row.share_pct), 3),
                        "lots": round(float(row.shares) / 1e8, 2),
                        "aum": round(float(row.aum) / 1e8, 1),
                        "cap": round(float(row.market_cap) / 1e8, 0),
                    }
                    for row in weekly.itertuples(index=False)
                ],
            }
        )
    return panels


def write_page(groups: list[dict], path: Path) -> None:
    asof = pd.Timestamp(groups[0]["asof"]).strftime("%Y-%m-%d")
    data = json.dumps(_panels(groups), ensure_ascii=False).replace("<", "\u003c")
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
  .meta { margin: 0; color: #333; font-size: 13px; line-height: 1.6; }
  ul { display: flex; flex-wrap: wrap; gap: 6px 18px; padding: 0; margin: 10px 0 4px; list-style: none; font-size: 13px; }
  .chart { position: relative; }
  canvas { width: 100%; height: 340px; display: block; cursor: crosshair; }
  .tip { min-height: 20px; margin: 2px 0 8px; color: #333; font-size: 12px; }
  footer { margin-top: 16px; color: #666; font-size: 12px; line-height: 1.7; }
</style>
</head>
<body>
<main>
  <h1>头部 ETF 持有规模占板块总市值</h1>
  <p class="lead">截至 __ASOF__。每组只留持有规模达到最大那只 10% 以上的基金，最多 4 只。上图蓝线是持有市值占板块总市值，下图蓝线是基金份额，用来看申购和赎回。</p>
  <div id="boards"></div>
  <footer>
    持有规模 = 基金份额 × 当日收盘价。份额来自上交所、深交所公布的 ETF 份额；收盘价来自本机通达信，基金价格按三位小数还原。
    总市值来自交易所每日股票概况：沪深300 用沪市主板 A + 科创板 + 深市主板 A + 创业板，科创50 用科创板，创业板用创业板。不含 B 股和北交所。
    周占比用当周最后一个交易日的份额和总市值。份额图只计交易所公布的基金份额，价格涨跌不算申购。仅供参考。
  </footer>
</main>
<script>
const panels = __DATA__;
const root = document.getElementById("boards");
panels.forEach((panel, index) => {
  const section = document.createElement("section");
  const funds = panel.members.map((item) => `${item.code} ${item.name} ${item.aum_yi} 亿 / ${item.shares_yi} 亿份`).join(" · ");
  section.innerHTML = `<h2>${panel.label}</h2>
    <p class="meta">${panel.members.length} 只 · 最新一周持有 ${panel.last_aum_yi} 亿，占${panel.market}总市值 ${panel.last_share}%（板块 ${panel.last_cap_yi} 亿）· 区间 ${panel.span}</p>
    <p class="meta">${panel.flow}</p>
    <ul><li>${funds}</li></ul>
    <div class="chart"><canvas id="c${index}"></canvas></div>
    <div class="tip" id="t${index}">鼠标移到图上看当天点位和占比</div>
    <div class="chart"><canvas id="f${index}"></canvas></div>
    <div class="tip" id="u${index}">鼠标移到图上看当天份额</div>`;
  root.appendChild(section);
  const ratio = document.getElementById("c" + index);
  const lots = document.getElementById("f" + index);
  draw(ratio, panel.points, panel.index, "占" + panel.market + "总市值", "share", "pct");
  draw(lots, panel.points, panel.index, "份额（亿份）", "lots", "lots");
  bind(ratio, document.getElementById("t" + index), panel, "share");
  bind(lots, document.getElementById("u" + index), panel, "lots");
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
  ctx.fillText(indexName + "（点）", pad.l, 12);
  ctx.fillStyle = "#1d4e89";
  ctx.textAlign = "right";
  ctx.fillText(rightName, width - pad.r, 12);
  canvas._geom = {pad, plotW, n, x};
}

function bind(canvas, tip, panel, mode) {
  canvas.addEventListener("mousemove", (event) => {
    const geom = canvas._geom;
    if (!geom) return;
    const rect = canvas.getBoundingClientRect();
    const px = event.clientX - rect.left;
    let nearest = 0;
    let best = Infinity;
    panel.points.forEach((_, i) => {
      const dist = Math.abs(geom.x(i) - px);
      if (dist < best) { best = dist; nearest = i; }
    });
    const p = panel.points[nearest];
    tip.textContent = mode === "lots"
      ? `${p.date}  ${panel.index} ${p.close.toFixed(2)}  份额 ${p.lots.toFixed(1)} 亿份`
      : `${p.date}  ${panel.index} ${p.close.toFixed(2)}  持有 ${p.aum} 亿 / ${panel.market} ${p.cap} 亿  占比 ${p.share.toFixed(2)}%`;
  });
}

window.addEventListener("resize", () => {
  panels.forEach((panel, index) => {
    draw(document.getElementById("c" + index), panel.points, panel.index, "占" + panel.market + "总市值", "share", "pct");
    draw(document.getElementById("f" + index), panel.points, panel.index, "份额（亿份）", "lots", "lots");
  });
});
</script>
</body>
</html>
"""
