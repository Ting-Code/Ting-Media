# -*- coding: utf-8 -*-
"""一期录屏：头部 ETF 九张图，每张一页。工作台用 screen-pack 母版，图用分析页原画法。

图表自己的显示规则（录屏规范只要求中间可用区显示全，不写死这些数）：
- 窄屏左右轴留白 32/38，轴文字 11px，标签距轴 4px；主图与区间条共用同一左右边。不要沿用分析页桌面的 62/56。
- 有区间条的长序列：主图默认最近约 5 年，区间条保留全部历史，可拖回全区间。短于 5 年的序列保持全长。
- 估值页（PE/PB/点位）：三条独立纵轴，无 1Y/3Y 按钮，区间条拖选；轴刻度数字隐藏，数值看悬浮。
"""
from __future__ import annotations

import html
import json
import sys
from datetime import date
from pathlib import Path

import pandas as pd

SRC = Path(__file__).resolve().parents[1] / "src"
sys.path.insert(0, str(SRC))

from _pathsetup import ensure_tool_srcs_on_path  # noqa: E402

ensure_tool_srcs_on_path()

from episode_path import episode_dir  # noqa: E402
from etf_share import build_etf_market_share  # noqa: E402
from render_report import _load_deck_template  # noqa: E402
from etf_valuation import build_board_valuations  # noqa: E402

KEEP_DRAW = {"draw", "drawAnomaly", "drawAnomalyBrush", "bindFlowBrush", "drawLineBrush"}
MOUNT_JS = r"""
const charts = __CHARTS__;
function paintOne(spec) {
  const range = spec.state.range;
  const rows = spec.points.slice(range.start, range.end + 1);
  if (!rows.length || !spec.plot.clientWidth) return;
  if (spec.kind === "val") {
    const hover = spec.hoverIndex == null ? null : {index: spec.hoverIndex};
    drawVal(spec.plot, rows, spec.peNow, hover);
    drawValBrush(spec.brush, spec.points, range);
  } else if (spec.kind === "flow") {
    drawAnomaly(spec.plot, rows, spec.index);
    drawAnomalyBrush(spec.brush, spec.points, range);
  } else {
    draw(spec.plot, rows, spec.index, spec.rightName, spec.rightKey, spec.rightKind);
    drawLineBrush(spec.brush, spec.points, range, spec.rightKey);
  }
}
// 长序列主图默认最近约 5 年；区间条仍是全部历史。短于 5 年的保持全长。
function defaultVisibleRange(points) {
  const end = Math.max(0, points.length - 1);
  if (!points.length) return {start: 0, end: 0};
  const last = Date.parse(points[end].date);
  const cutoff = last - 5 * 365.25 * 24 * 3600 * 1000;
  let start = 0;
  for (let i = 0; i <= end; i++) {
    if (Date.parse(points[i].date) >= cutoff) { start = i; break; }
  }
  return {start, end};
}
function mountCharts() {
  document.querySelectorAll(".with-range").forEach((box) => {
    const spec = charts[Number(box.dataset.i)];
    spec.plot = box.querySelector(".plot");
    spec.brush = box.querySelector(".range");
    spec.state = {range: defaultVisibleRange(spec.points)};
    const paint = () => paintOne(spec);
    spec.paint = paint;
    paint();
    bindFlowBrush(spec.brush, spec.points, spec.state, paint);
    if (spec.kind === "val") bindValHover(spec.plot, spec, paint);
  });
}
window.addEventListener("resize", () => charts.forEach((spec) => spec.paint && spec.paint()));
function bootCharts() {
  mountCharts();
  requestAnimationFrame(() => charts.forEach((spec) => spec.paint && spec.paint()));
}
if (document.readyState === "complete") bootCharts();
else window.addEventListener("load", bootCharts);
"""



VAL_JS = r"""
function finiteVals(values) {
  return values.filter((v) => v != null && Number.isFinite(v));
}
function paddedRange(values, pad) {
  const nums = finiteVals(values);
  if (!nums.length) return null;
  let lo = Math.min(...nums);
  let hi = Math.max(...nums);
  if (lo === hi) {
    const delta = Math.abs(lo) * 0.1 || 1;
    return {lo: lo - delta, hi: hi + delta};
  }
  const span = hi - lo;
  return {lo: lo - span * pad, hi: hi + span * pad};
}
function drawVal(canvas, points, peNow, hover) {
  const dpr = window.devicePixelRatio || 1;
  const width = canvas.clientWidth;
  const height = canvas.clientHeight;
  canvas.width = Math.max(1, Math.floor(width * dpr));
  canvas.height = Math.max(1, Math.floor(height * dpr));
  const ctx = canvas.getContext("2d");
  ctx.setTransform(dpr, 0, 0, dpr, 0, 0);
  const pad = {l: 16, r: 16, t: 28, b: 28};
  const plotW = width - pad.l - pad.r;
  const plotH = height - pad.t - pad.b;
  const n = points.length;
  const peRange = paddedRange(points.map((p) => p.pe), 0.08);
  const pbRange = paddedRange(points.map((p) => p.pb), 0.08);
  const priceRange = paddedRange(points.map((p) => p.price), 0.08);
  if (peNow != null && peRange) {
    peRange.lo = Math.min(peRange.lo, peNow);
    peRange.hi = Math.max(peRange.hi, peNow);
  }
  const x = (i) => pad.l + (n < 2 ? plotW / 2 : (i / (n - 1)) * plotW);
  const yOf = (range, v) => pad.t + (range.hi - v) / (range.hi - range.lo || 1) * plotH;
  ctx.clearRect(0, 0, width, height);
  ctx.strokeStyle = "rgba(62,68,81,.85)";
  ctx.lineWidth = 1;
  for (let i = 0; i <= 4; i++) {
    const y = pad.t + (plotH * i) / 4;
    ctx.beginPath();
    ctx.moveTo(pad.l, y);
    ctx.lineTo(width - pad.r, y);
    ctx.stroke();
  }
  if (peNow != null && peRange) {
    const y = yOf(peRange, peNow);
    ctx.setLineDash([6, 5]);
    ctx.strokeStyle = "#ef5350";
    ctx.beginPath();
    ctx.moveTo(pad.l, y);
    ctx.lineTo(width - pad.r, y);
    ctx.stroke();
    ctx.setLineDash([]);
  }
  const series = [
    {key: "pe", color: "#ef5350", range: peRange, name: "PE"},
    {key: "pb", color: "#61afef", range: pbRange, name: "PB"},
    {key: "price", color: "#98c379", range: priceRange, name: "点位"},
  ];
  series.forEach((item) => {
    if (!item.range) return;
    ctx.strokeStyle = item.color;
    ctx.fillStyle = item.color;
    ctx.lineWidth = 2;
    let started = false;
    ctx.beginPath();
    points.forEach((p, i) => {
      const v = p[item.key];
      if (v == null || !Number.isFinite(v)) { started = false; return; }
      const cx = x(i);
      const cy = yOf(item.range, v);
      if (!started) { ctx.moveTo(cx, cy); started = true; }
      else ctx.lineTo(cx, cy);
    });
    ctx.stroke();
    points.forEach((p, i) => {
      const v = p[item.key];
      if (v == null || !Number.isFinite(v)) return;
      ctx.beginPath();
      ctx.arc(x(i), yOf(item.range, v), 2.6, 0, Math.PI * 2);
      ctx.fill();
    });
  });
  ctx.font = "11px Microsoft YaHei, sans-serif";
  ctx.textBaseline = "top";
  if (hover && points[hover.index]) {
    const p = points[hover.index];
    const cx = x(hover.index);
    ctx.strokeStyle = "rgba(171,178,191,.45)";
    ctx.lineWidth = 1;
    ctx.beginPath();
    ctx.moveTo(cx, pad.t);
    ctx.lineTo(cx, pad.t + plotH);
    ctx.stroke();
    const pe = p.pe == null ? "—" : p.pe.toFixed(2);
    const pb = p.pb == null ? "—" : p.pb.toFixed(2);
    const price = p.price == null ? "—" : p.price.toFixed(2);
    const flag = p.incomplete ? "  当季未结束" : "";
    ctx.fillStyle = "#e6e6e6";
    ctx.textAlign = "left";
    ctx.fillText(p.date + "  PE " + pe + "  PB " + pb + "  点位 " + price + flag, pad.l, 6);
  } else {
    let lx = pad.l;
    series.forEach((item) => {
      ctx.fillStyle = item.color;
      ctx.fillRect(lx, 9, 8, 8);
      ctx.fillStyle = "#abb2bf";
      ctx.textAlign = "left";
      ctx.fillText(item.name, lx + 11, 6);
      lx += 11 + ctx.measureText(item.name).width + 12;
    });
    if (peNow != null) {
      ctx.fillStyle = "#ef5350";
      ctx.textAlign = "right";
      ctx.fillText("当前 PE " + peNow.toFixed(1), width - pad.r, 6);
    }
  }
  ctx.fillStyle = "#9da5b4";
  ctx.textBaseline = "alphabetic";
  if (points.length) {
    ctx.textAlign = "left";
    ctx.fillText(points[0].date.slice(0, 7), pad.l, height - 8);
    ctx.textAlign = "right";
    ctx.fillText(points[points.length - 1].date.slice(0, 7), width - pad.r, height - 8);
  }
  canvas._geom = {n, x, pad, plotW, plotH};
}
function drawValBrush(canvas, points, range) {
  const dpr = window.devicePixelRatio || 1;
  const width = canvas.clientWidth;
  const height = canvas.clientHeight;
  canvas.width = Math.max(1, Math.floor(width * dpr));
  canvas.height = Math.max(1, Math.floor(height * dpr));
  const ctx = canvas.getContext("2d");
  ctx.setTransform(dpr, 0, 0, dpr, 0, 0);
  const pad = {l: 16, r: 16, t: 6, b: 18};
  const plotW = width - pad.l - pad.r;
  const plotH = height - pad.t - pad.b;
  const n = points.length;
  const peRange = paddedRange(points.map((p) => p.pe), 0.08) || {lo: 0, hi: 1};
  const x = (i) => pad.l + (n < 2 ? plotW / 2 : (i / (n - 1)) * plotW);
  const y = (v) => pad.t + (peRange.hi - v) / (peRange.hi - peRange.lo || 1) * plotH;
  ctx.clearRect(0, 0, width, height);
  ctx.strokeStyle = "#ef5350";
  ctx.lineWidth = 1.2;
  let started = false;
  ctx.beginPath();
  points.forEach((p, i) => {
    if (p.pe == null || !Number.isFinite(p.pe)) { started = false; return; }
    const cx = x(i);
    const cy = y(p.pe);
    if (!started) { ctx.moveTo(cx, cy); started = true; }
    else ctx.lineTo(cx, cy);
  });
  ctx.stroke();
  const x0 = x(range.start);
  const x1 = x(range.end);
  ctx.fillStyle = "rgba(97, 175, 239, 0.22)";
  ctx.fillRect(x0, pad.t, Math.max(2, x1 - x0), plotH);
  ctx.strokeStyle = "#61afef";
  ctx.lineWidth = 1.5;
  ctx.strokeRect(x0, pad.t, Math.max(2, x1 - x0), plotH);
  ctx.fillStyle = "#61afef";
  ctx.fillRect(x0 - 2, pad.t, 4, plotH);
  ctx.fillRect(x1 - 2, pad.t, 4, plotH);
  ctx.font = "11px Microsoft YaHei, sans-serif";
  ctx.fillStyle = "#9da5b4";
  if (points.length) {
    ctx.textAlign = "left";
    ctx.fillText(points[0].date.slice(0, 7), pad.l, height - 4);
    ctx.textAlign = "right";
    ctx.fillText(points[points.length - 1].date.slice(0, 7), width - pad.r, height - 4);
  }
  canvas._geom = {n, x, pad};
}
function bindValHover(plot, spec, paint) {
  plot.addEventListener("mousemove", (event) => {
    const geom = plot._geom;
    const range = spec.state.range;
    const rows = spec.points.slice(range.start, range.end + 1);
    if (!geom || !rows.length) return;
    const px = event.clientX - plot.getBoundingClientRect().left;
    let nearest = 0, best = Infinity;
    rows.forEach((_, i) => {
      const dist = Math.abs(geom.x(i) - px);
      if (dist < best) { best = dist; nearest = i; }
    });
    if (spec.hoverIndex !== nearest) {
      spec.hoverIndex = nearest;
      paint();
    }
  });
  plot.addEventListener("mouseleave", () => {
    if (spec.hoverIndex == null) return;
    spec.hoverIndex = null;
    paint();
  });
}
"""


def _tool_colors(draw_js: str) -> str:
    """分析页的画法，换成录屏深色主题。序列和区间条不动。"""
    swaps = (
        ("rgba(29, 78, 137, 0.16)", "rgba(97, 175, 239, 0.22)"),
        ("#1d4e89", "#61afef"),
        ("#d84a4a", "#ef5350"),
        ("#1c9a62", "#26a69a"),
        ("#ececec", "rgba(62,68,81,.85)"),
        ("#c8c8c8", "#5c6370"),
        ("#222", "#e6e6e6"),
        ("#666", "#9da5b4"),
        ("#888", "#5c6370"),
    )
    for old_color, new_color in swaps:
        draw_js = draw_js.replace(old_color, new_color)
    return draw_js



def _phone_pads(draw_js: str) -> str:
    """按本文件图表规则，把分析页桌面轴边距收到窄屏 32/38，轴文字 11px，标签距轴 4px。"""
    swaps = (
        ("const pad = {l: 62, r: 56, t: 18, b: 32};", "const pad = {l: 32, r: 38, t: 18, b: 32};"),
        ("const pad = {l: 62, r: 64, t: 18, b: 32};", "const pad = {l: 32, r: 38, t: 18, b: 32};"),
        ("const pad = {l: 62, r: 64, t: 6, b: 18};", "const pad = {l: 32, r: 38, t: 6, b: 18};"),
        ("const pad = {l: 62, r: 56, t: 6, b: 18};", "const pad = {l: 32, r: 38, t: 6, b: 18};"),
        ('ctx.font = "12px Microsoft YaHei, sans-serif";', 'ctx.font = "11px Microsoft YaHei, sans-serif";'),
        ("pad.l - 8", "pad.l - 4"),
        ("width - pad.r + 8", "width - pad.r + 4"),
    )
    for old, new in swaps:
        if old not in draw_js:
            raise RuntimeError("分析页轴边距字面量缺失: %s" % old)
        draw_js = draw_js.replace(old, new)
    return draw_js


def _source_draw_js() -> str:
    page = Path(__file__).resolve().parents[2] / "stock-screener" / "src" / "etf_page.py"
    text = page.read_text(encoding="utf-8")
    start = text.find("function draw(")
    chunk = text[start:text.find("function mountSeries(")]
    blocks = []
    current: list[str] = []
    name = ""
    for line in chunk.splitlines():
        if line.startswith("function "):
            if name in KEEP_DRAW:
                blocks.append("\n".join(current))
            current = [line]
            name = line.split("function ", 1)[1].split("(", 1)[0]
        else:
            current.append(line)
    if name in KEEP_DRAW:
        blocks.append("\n".join(current))
    missing = KEEP_DRAW.difference(block.split("function ", 1)[1].split("(", 1)[0] for block in blocks)
    if missing:
        raise RuntimeError("分析页画图函数缺失: %s" % ",".join(sorted(missing)))
    return "\n".join(blocks)


def _weekly_points(group: dict) -> list[dict]:
    rows = []
    for row in group["weekly"].itertuples(index=False):
        rows.append(
            {
                "date": pd.Timestamp(row.date).strftime("%Y-%m-%d"),
                "open": round(float(row.open), 2),
                "high": round(float(row.high), 2),
                "low": round(float(row.low), 2),
                "close": round(float(row.close), 2),
                "share": None if pd.isna(row.share_pct) else round(float(row.share_pct), 3),
                "lots": round(float(row.shares) / 1e8, 2),
            }
        )
    return rows


def _slide(index: int, total: int, title: str, tag: str, script: str, chart_i: int) -> str:
    script_attr = html.escape(script, quote=True).replace("\n", "&#10;")
    box = (
        '<div class="chart-box with-range" data-i="%d">'
        '<canvas class="plot"></canvas><canvas class="range"></canvas></div>'
    ) % chart_i
    return (
        '<section class="slide slide-chart" id="slide-%d" data-page="%d" data-title="%s" data-script="%s">'
        '<div class="slide-inner"><h2>%s</h2><div class="panel">%s</div></div></section>'
    ) % (
        index,
        index,
        html.escape(title, quote=True),
        script_attr,
        html.escape(title),
        box,
    )


def _pages(groups: list[dict]) -> tuple[list[dict], list[dict]]:
    slides = []
    charts = []
    for group in groups:
        label = group["label"]
        index_name = group["index_name"]
        market = group["market_name"]
        flow = group["flow"]["text"]
        points = _weekly_points(group)
        slides.append(
            {
                "title": "%s持有规模" % label,
                "tag": "占%s总市值" % market,
                "script": (
                    "这一页是%s头部 ETF 的持有规模。\n"
                    "蓝线是基金份额乘收盘价，除以%s总市值。头部按当周规模重选。\n"
                    "总市值大约从 2022 年起才有，所以这张图从那时候画。\n"
                    "只描述位置，不给操作建议。数据仅供参考。"
                ) % (label, market),
            }
        )
        charts.append(
            {
                "kind": "ratio",
                "index": index_name,
                "rightName": "占%s总市值" % market,
                "rightKey": "share",
                "rightKind": "pct",
                "points": [row for row in points if row["share"] is not None],
            }
        )
        slides.append(
            {
                "title": "%s基金份额" % label,
                "tag": "当周头部合计",
                "script": (
                    "这一页只看%s的基金份额。\n%s\n份额上升是申购，下降是赎回，不含价格涨跌。数据仅供参考。"
                ) % (label, flow),
            }
        )
        charts.append(
            {
                "kind": "lots",
                "index": index_name,
                "rightName": "份额（亿份）",
                "rightKey": "lots",
                "rightKind": "lots",
                "points": points,
            }
        )
        rule = group["anomaly_rule"]
        slides.append(
            {
                "title": "%s申购异动" % label,
                "tag": "周净申购",
                "script": (
                    "这一页看%s头部的周净申购。\n"
                    "深红是指数下跌时多只一起大额申购，橙色是上涨时仍多只同步，绿色是大额赎回。\n"
                    "份额看不出账户，不能据此认定是某一家机构。数据仅供参考。"
                ) % label,
            }
        )
        charts.append(
            {
                "kind": "flow",
                "index": index_name,
                "rightName": "",
                "rightKey": "total",
                "rightKind": "lots",
                "points": group["anomaly"],
                "rule": {
                    "total": int(rule["total"]),
                    "sync": int(rule["sync"]),
                    "each": int(rule["each"]),
                },
            }
        )
    return slides, charts



def _render_episode(slides: list[dict], charts: list[dict], asof: str, out: Path, note: str) -> Path:
    body = "\n".join(
        _slide(i, len(slides), page["title"], page.get("tag") or "", page["script"], i - 1)
        for i, page in enumerate(slides, start=1)
    )
    template = _load_deck_template()
    start = template.find('<div class="deck" id="deck">')
    end = template.find("      </div>", template.find('id="slide-end"'))
    if start < 0 or end < 0:
        raise RuntimeError("deck template markers missing")
    html_text = template[: start + len('<div class="deck" id="deck">')] + "\n" + body + "\n" + template[end:]
    html_text = html_text.replace("__NAME__", "头部ETF").replace("__CODE__", "十二张图").replace("__ASOF__", asof)
    html_text = html_text.replace('<script src="https://cdn.plot.ly/plotly-2.35.2.min.js"></script>', "")
    data = json.dumps(charts, ensure_ascii=False).replace("<", "\\u003c")
    extra = (
        "<script>\n"
        + _tool_colors(_phone_pads(_source_draw_js()))
        + "\n"
        + VAL_JS
        + "\n"
        + MOUNT_JS.replace("__CHARTS__", data)
        + "\n</script>\n"
    )
    html_text = html_text.replace("</body>", extra + "</body>")
    out.mkdir(parents=True, exist_ok=True)
    page_path = out / "index.html"
    page_path.write_text(html_text, encoding="utf-8")
    meta = {
        "theme": "头部ETF持有规模",
        "date": out.name.split("_", 1)[0],
        "asof": asof,
        "cache": "cache/etf_market_share_%s" % asof,
        "pages": [page["title"] for page in slides],
        "note": note,
    }
    (out / "meta.json").write_text(json.dumps(meta, ensure_ascii=False, indent=2), encoding="utf-8")
    return page_path


def _append_valuations(slides: list[dict], charts: list[dict], asof: str) -> None:
    for page in build_board_valuations(asof):
        slides.append({"title": page["title"], "tag": page["tag"], "script": page["script"]})
        charts.append(page["chart"])


def _reuse_episode(folder: Path) -> tuple[list[dict], list[dict], str]:
    import html as html_lib
    import re

    html_text = (folder / "index.html").read_text(encoding="utf-8")
    meta = json.loads((folder / "meta.json").read_text(encoding="utf-8"))
    match = re.search(r"const charts = (\[.*?\]);\s*function paintOne", html_text, re.S)
    if not match:
        raise RuntimeError("existing episode charts not found")
    charts = [item for item in json.loads(match.group(1)) if item.get("kind") in {"ratio", "lots", "flow"}]
    slides = []
    for section in re.finditer(
        r'<section class="slide slide-chart"[^>]*data-title="([^"]*)"[^>]*data-script="([^"]*)"',
        html_text,
    ):
        title = html_lib.unescape(section.group(1))
        if title.endswith("估值"):
            continue
        script = html_lib.unescape(section.group(2)).replace("&#10;", "\n")
        slides.append({"title": title, "tag": "", "script": script})
    if len(slides) != 9 or len(charts) != 9:
        raise RuntimeError("expected 9 ETF pages, got %d slides, %d charts" % (len(slides), len(charts)))
    return slides, charts, meta["asof"]


def main(argv: list[str] | None = None) -> int:
    argv = list(sys.argv[1:] if argv is None else argv)
    note = (
        "前九页为头部 ETF 规模/份额/异动；后三页为对应板块估值（点位用官方指数，"
        "PE/PB 用乐咕滚动加权；科创 PE/PB 为科创板整体，创业板 PE/PB 为创业板50）。生成数据仅供参考。"
    )
    if argv and argv[0] == "--reuse":
        folder = Path(argv[1])
        slides, charts, asof = _reuse_episode(folder)
        _append_valuations(slides, charts, asof)
        page_path = _render_episode(slides, charts, asof, folder, note)
        print(page_path)
        return 0
    groups = build_etf_market_share()
    asof = pd.Timestamp(groups[0]["asof"]).strftime("%Y-%m-%d")
    slides, charts = _pages(groups)
    _append_valuations(slides, charts, asof)
    out = episode_dir(niche="finance", theme="头部ETF持有规模", day=date.today())
    page_path = _render_episode(slides, charts, asof, out, note)
    print(page_path)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
