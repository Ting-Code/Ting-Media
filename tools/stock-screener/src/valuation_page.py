"""单股 PE/PB/股价静态网页。普通横版页面，不是录屏 HTML。

交互跟 ETF 分析页同一套：主图 + 下方色带选区间。不要 1Y/3Y/5Y，也不要平移/框选按钮。
"""

from __future__ import annotations

import json
from pathlib import Path

import pandas as pd


def _esc(value) -> str:
    text = "" if value is None else str(value)
    return (
        text.replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
        .replace('"', "&quot;")
    )


def _fmt(value, nd=2, suffix=""):
    if value is None:
        return "—"
    try:
        if pd.isna(value):
            return "—"
    except TypeError:
        pass
    return f"{float(value):.{nd}f}{suffix}"


def _num(value, nd=None):
    if value is None:
        return None
    try:
        if pd.isna(value):
            return None
    except TypeError:
        pass
    number = float(value)
    if nd is None:
        return number
    return round(number, nd)


def _points(series: pd.DataFrame) -> list[dict]:
    rows = []
    for row in series.itertuples(index=False):
        rows.append(
            {
                "date": pd.Timestamp(row.anchor_date).strftime("%Y-%m-%d"),
                "quarter": pd.Timestamp(row.quarter_end).strftime("%Y-%m-%d"),
                "price": _num(row.price, 2),
                "pe": _num(getattr(row, "pe", None), 2),
                "pb": _num(getattr(row, "pb", None), 2),
                "incomplete": bool(getattr(row, "incomplete_quarter", False)),
            }
        )
    return rows


def write_valuation_page(name: str, code: str, series: pd.DataFrame, summary: dict, out_dir: Path) -> Path:
    out_dir = Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    if series is not None and not series.empty:
        series.to_csv(out_dir / "series.csv", index=False, encoding="utf-8-sig")
    (out_dir / "snapshot.json").write_text(
        json.dumps(summary, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    points = [] if series is None or series.empty else _points(series)
    pe_now = _num(summary.get("pe"), 2)
    hk = str(summary.get("market") or "").lower() == "hk" or str(summary.get("currency_price") or "").upper() == "HKD"
    lead = _HK_LEAD if hk else _A_LEAD
    footer = _HK_FOOT if hk else _A_FOOT
    payload = {
        "points": points,
        "pe_now": pe_now,
        "name": name,
        "code": code,
    }
    data = json.dumps(payload, ensure_ascii=False).replace("<", "<")
    page = (
        _PAGE.replace("__TITLE__", _esc(f"{name} {code} PE"))
        .replace("__NAME__", _esc(name))
        .replace("__CODE__", _esc(code))
        .replace("__LEAD__", lead)
        .replace("__FOOTER__", footer)
        .replace("__ASOF__", _esc(summary.get("asof") or "—"))
        .replace("__PRICE__", _esc(_fmt(summary.get("price"), 2)))
        .replace("__PE__", _esc(_fmt(pe_now, 2)))
        .replace("__PE_PCT__", _esc(_fmt(summary.get("pe_percentile"), 1, "%")))
        .replace("__PB__", _esc(_fmt(summary.get("pb"), 2)))
        .replace("__PB_PCT__", _esc(_fmt(summary.get("pb_percentile"), 1, "%")))
        .replace("__DIV__", _esc(_fmt(summary.get("div_yield_pct"), 2, "%")))
        .replace("__DIV_PCT__", _esc(_fmt(summary.get("div_percentile"), 1, "%")))
        .replace("__REPORT__", _esc(summary.get("report_date") or "—"))
        .replace("__DATA__", data)
    )
    path = out_dir / "index.html"
    path.write_text(page, encoding="utf-8")
    return path



_A_LEAD = "截至 __ASOF__。每个点都用上一季单季扣非净利润年化（×4），配该季末不复权收盘价。当季未结束时用最新收盘。最新一点的盈利来自报告期 __REPORT__。"
_A_FOOT = "股息率是最近四个已结束报告期里已经实施的现金分红合计（不含特别分红），除以最新不复权收盘价，只出现在上面的数字里。单季扣非小于或等于 0 时，该季 PE 留空。生成数据仅供参考，不构成投资建议。"
_HK_LEAD = "截至 __ASOF__。每个点都用上一季单季股东应占溢利对应的基本每股盈利年化（×4），配该季末不复权港股收盘价，再按当日港币人民币中间价折成人民币计算 PE/PB。当季未结束时用最新完整收盘。最新一点的盈利来自报告期 __REPORT__。绿线股价为港元。"
_HK_FOOT = "本次未计算港股股息率。单季盈利小于或等于 0 时，该季 PE 留空。生成数据仅供参考，不构成投资建议。"


_PAGE = '<!DOCTYPE html>\n<html lang="zh-CN">\n<head>\n<meta charset="utf-8">\n<meta name="viewport" content="width=device-width, initial-scale=1">\n<title>__TITLE__</title>\n<style>\n  body { margin: 0; background: #f3f4f6; color: #1a1a1a; font-family: "Microsoft YaHei", "PingFang SC", sans-serif; }\n  main { max-width: 1080px; margin: 0 auto; padding: 32px 20px 56px; }\n  h1 { font-size: 26px; line-height: 1.3; margin: 0 0 8px; }\n  .lead { margin: 0; color: #4b4b4b; font-size: 14px; line-height: 1.7; }\n  section { background: #fff; border: 1px solid #e3e3e3; margin-top: 18px; padding: 16px 16px 8px; }\n  .stats { display: flex; flex-wrap: wrap; gap: 8px 22px; margin: 12px 0 0; padding: 0; list-style: none; font-size: 15px; }\n  .stats b { font-weight: 650; }\n  .legend { display: flex; flex-wrap: wrap; gap: 8px 18px; margin: 10px 0 6px; padding: 0; list-style: none; font-size: 13px; color: #333; }\n  .legend i { display: inline-block; width: 12px; height: 3px; margin-right: 6px; vertical-align: middle; }\n  .legend .pe { background: #c0392b; }\n  .legend .pb { background: #1d4e89; }\n  .legend .price { background: #1c7c4a; }\n  .legend .now { background: #c0392b; height: 0; border-top: 2px dashed #c0392b; }\n  .axis { margin: 0 0 6px; color: #444; font-size: 13px; line-height: 1.55; }\n  .chart { position: relative; }\n  canvas { width: 100%; height: 420px; display: block; cursor: crosshair; }\n  .brush canvas { height: 72px; cursor: ew-resize; }\n  .tip { min-height: 20px; margin: 2px 0 8px; color: #333; font-size: 12px; }\n  footer { margin-top: 16px; color: #666; font-size: 12px; line-height: 1.7; }\n</style>\n</head>\n<body>\n<main>\n  <h1>__NAME__ __CODE__</h1>\n  <p class="lead">__LEAD__</p>\n  <ul class="stats">\n    <li>股价 <b>__PRICE__</b></li>\n    <li>PE <b>__PE__</b> · 历史分位 __PE_PCT__</li>\n    <li>PB <b>__PB__</b> · 历史分位 __PB_PCT__</li>\n    <li>股息率 <b>__DIV__</b> · 历史分位 __DIV_PCT__</li>\n  </ul>\n  <section>\n    <p class="axis">红线是 PE，蓝线是 PB，绿线是季度末股价。三条线各用自己的纵轴，按当前选中区间各自拉满，不共用刻度，也不做末点归一。纵轴数字隐藏，鼠标移到点上看真值。缺值的季度断开，不连成假线。红色虚线是当前 PE。</p>\n    <ul class="legend">\n      <li><i class="pe"></i>PE</li>\n      <li><i class="pb"></i>PB</li>\n      <li><i class="price"></i>股价</li>\n      <li><i class="now"></i>当前 PE</li>\n    </ul>\n    <div class="chart"><canvas id="main"></canvas></div>\n    <div class="brush"><canvas id="brush"></canvas></div>\n    <p class="axis" id="range"></p>\n    <div class="tip" id="tip">鼠标移到图上看 PE、PB 和股价。下方色带拖动选区，拖两端改范围。</div>\n  </section>\n  <footer>\n    __FOOTER__\n  </footer>\n</main>\n<script>\nconst pack = __DATA__;\nconst all = pack.points || [];\nconst peNow = pack.pe_now;\nconst state = {range: {start: 0, end: Math.max(0, all.length - 1)}};\n\nfunction slice() {\n  return all.slice(state.range.start, state.range.end + 1);\n}\n\nfunction finite(values) {\n  return values.filter((v) => v != null && Number.isFinite(v));\n}\n\nfunction padded(values, pad) {\n  const nums = finite(values);\n  if (!nums.length) return null;\n  let lo = Math.min(...nums);\n  let hi = Math.max(...nums);\n  if (lo === hi) {\n    const delta = Math.abs(lo) * 0.1 || 1;\n    return {lo: lo - delta, hi: hi + delta};\n  }\n  const span = hi - lo;\n  return {lo: lo - span * pad, hi: hi + span * pad};\n}\n\nfunction drawMain(canvas, points) {\n  const dpr = window.devicePixelRatio || 1;\n  const width = canvas.clientWidth;\n  const height = canvas.clientHeight;\n  canvas.width = Math.max(1, Math.floor(width * dpr));\n  canvas.height = Math.max(1, Math.floor(height * dpr));\n  const ctx = canvas.getContext("2d");\n  ctx.setTransform(dpr, 0, 0, dpr, 0, 0);\n  const pad = {l: 28, r: 28, t: 18, b: 34};\n  const plotW = width - pad.l - pad.r;\n  const plotH = height - pad.t - pad.b;\n  const n = points.length;\n  const peRange = padded(points.map((p) => p.pe), 0.08);\n  const pbRange = padded(points.map((p) => p.pb), 0.08);\n  const priceRange = padded(points.map((p) => p.price), 0.08);\n  if (peNow != null && peRange) {\n    peRange.lo = Math.min(peRange.lo, peNow);\n    peRange.hi = Math.max(peRange.hi, peNow);\n  }\n  const x = (i) => pad.l + (n < 2 ? plotW / 2 : (i / (n - 1)) * plotW);\n  const yOf = (range, v) => pad.t + (range.hi - v) / (range.hi - range.lo || 1) * plotH;\n  ctx.clearRect(0, 0, width, height);\n  ctx.strokeStyle = "#ececec";\n  ctx.lineWidth = 1;\n  for (let i = 0; i <= 4; i++) {\n    const y = pad.t + (plotH * i) / 4;\n    ctx.beginPath();\n    ctx.moveTo(pad.l, y);\n    ctx.lineTo(width - pad.r, y);\n    ctx.stroke();\n  }\n  if (peNow != null && peRange) {\n    const y = yOf(peRange, peNow);\n    ctx.setLineDash([6, 5]);\n    ctx.strokeStyle = "#c0392b";\n    ctx.beginPath();\n    ctx.moveTo(pad.l, y);\n    ctx.lineTo(width - pad.r, y);\n    ctx.stroke();\n    ctx.setLineDash([]);\n    ctx.fillStyle = "#c0392b";\n    ctx.font = "12px Microsoft YaHei, sans-serif";\n    ctx.textAlign = "left";\n    ctx.fillText("当前 PE " + peNow.toFixed(1), pad.l + 4, Math.max(pad.t + 12, y - 6));\n  }\n  const series = [\n    {key: "pe", color: "#c0392b", range: peRange},\n    {key: "pb", color: "#1d4e89", range: pbRange},\n    {key: "price", color: "#1c7c4a", range: priceRange},\n  ];\n  series.forEach((item) => {\n    if (!item.range) return;\n    ctx.strokeStyle = item.color;\n    ctx.fillStyle = item.color;\n    ctx.lineWidth = 2;\n    let started = false;\n    ctx.beginPath();\n    points.forEach((p, i) => {\n      const v = p[item.key];\n      if (v == null || !Number.isFinite(v)) {\n        started = false;\n        return;\n      }\n      const cx = x(i);\n      const cy = yOf(item.range, v);\n      if (!started) {\n        ctx.moveTo(cx, cy);\n        started = true;\n      } else {\n        ctx.lineTo(cx, cy);\n      }\n    });\n    ctx.stroke();\n    points.forEach((p, i) => {\n      const v = p[item.key];\n      if (v == null || !Number.isFinite(v)) return;\n      const cx = x(i);\n      const cy = yOf(item.range, v);\n      ctx.beginPath();\n      ctx.arc(cx, cy, 3.2, 0, Math.PI * 2);\n      ctx.fill();\n    });\n  });\n  ctx.fillStyle = "#666";\n  ctx.font = "12px Microsoft YaHei, sans-serif";\n  if (points.length) {\n    ctx.textAlign = "left";\n    ctx.fillText(points[0].date.slice(0, 7), pad.l, height - 8);\n    ctx.textAlign = "right";\n    ctx.fillText(points[points.length - 1].date.slice(0, 7), width - pad.r, height - 8);\n  }\n  canvas._geom = {n, x, pad, plotW, plotH};\n}\nfunction drawBrush(canvas, points, range) {\n  const dpr = window.devicePixelRatio || 1;\n  const width = canvas.clientWidth;\n  const height = canvas.clientHeight;\n  canvas.width = Math.max(1, Math.floor(width * dpr));\n  canvas.height = Math.max(1, Math.floor(height * dpr));\n  const ctx = canvas.getContext("2d");\n  ctx.setTransform(dpr, 0, 0, dpr, 0, 0);\n  const pad = {l: 28, r: 28, t: 8, b: 18};\n  const plotW = width - pad.l - pad.r;\n  const plotH = height - pad.t - pad.b;\n  const n = points.length;\n  const peRange = padded(points.map((p) => p.pe), 0.08) || {lo: 0, hi: 1};\n  const x = (i) => pad.l + (n < 2 ? plotW / 2 : (i / (n - 1)) * plotW);\n  const y = (v) => pad.t + (peRange.hi - v) / (peRange.hi - peRange.lo || 1) * plotH;\n  ctx.clearRect(0, 0, width, height);\n  ctx.strokeStyle = "#c0392b";\n  ctx.lineWidth = 1.2;\n  let started = false;\n  ctx.beginPath();\n  points.forEach((p, i) => {\n    if (p.pe == null || !Number.isFinite(p.pe)) {\n      started = false;\n      return;\n    }\n    const cx = x(i);\n    const cy = y(p.pe);\n    if (!started) {\n      ctx.moveTo(cx, cy);\n      started = true;\n    } else {\n      ctx.lineTo(cx, cy);\n    }\n  });\n  ctx.stroke();\n  const x0 = x(range.start);\n  const x1 = x(range.end);\n  ctx.fillStyle = "rgba(29, 78, 137, 0.16)";\n  ctx.fillRect(x0, pad.t, Math.max(2, x1 - x0), plotH);\n  ctx.strokeStyle = "#1d4e89";\n  ctx.lineWidth = 1.5;\n  ctx.strokeRect(x0, pad.t, Math.max(2, x1 - x0), plotH);\n  ctx.fillStyle = "#1d4e89";\n  ctx.fillRect(x0 - 2, pad.t, 4, plotH);\n  ctx.fillRect(x1 - 2, pad.t, 4, plotH);\n  ctx.font = "11px Microsoft YaHei, sans-serif";\n  ctx.fillStyle = "#666";\n  if (points.length) {\n    ctx.textAlign = "left";\n    ctx.fillText(points[0].date.slice(0, 7), pad.l, height - 4);\n    ctx.textAlign = "right";\n    ctx.fillText(points[points.length - 1].date.slice(0, 7), width - pad.r, height - 4);\n  }\n  canvas._geom = {n, x, pad};\n}\n\nfunction paint() {\n  const points = slice();\n  drawMain(document.getElementById("main"), points);\n  drawBrush(document.getElementById("brush"), all, state.range);\n  const label = document.getElementById("range");\n  if (points.length) {\n    label.textContent = "显示 " + points[0].date + " 至 " + points[points.length - 1].date + "，共 " + points.length + " 个季度。在下方色带上拖动选区，拖两端改范围。主图按选中区间重新定三条纵轴。";\n  } else {\n    label.textContent = "没有可画的季度点。";\n  }\n}\n\nfunction bindTip(canvas, tip) {\n  canvas.addEventListener("mousemove", (event) => {\n    const geom = canvas._geom;\n    const points = slice();\n    if (!geom || !points.length) return;\n    const px = event.clientX - canvas.getBoundingClientRect().left;\n    let nearest = 0;\n    let best = Infinity;\n    points.forEach((_, i) => {\n      const dist = Math.abs(geom.x(i) - px);\n      if (dist < best) {\n        best = dist;\n        nearest = i;\n      }\n    });\n    const p = points[nearest];\n    const pe = p.pe == null ? "—" : p.pe.toFixed(2);\n    const pb = p.pb == null ? "—" : p.pb.toFixed(2);\n    const price = p.price == null ? "—" : p.price.toFixed(2);\n    const flag = p.incomplete ? " · 当季未结束，用最新收盘" : "";\n    tip.textContent = p.date + "  PE " + pe + "  PB " + pb + "  股价 " + price + flag;\n  });\n}\n\nfunction bindBrush(canvas) {\n  let drag = null;\n  const indexAt = (event) => {\n    const geom = canvas._geom;\n    const px = event.clientX - canvas.getBoundingClientRect().left;\n    let nearest = 0;\n    let best = Infinity;\n    for (let i = 0; i < geom.n; i++) {\n      const dist = Math.abs(geom.x(i) - px);\n      if (dist < best) {\n        best = dist;\n        nearest = i;\n      }\n    }\n    return nearest;\n  };\n  const clampRange = (start, end) => {\n    const span = Math.max(4, end - start);\n    let left = start;\n    let right = start + span;\n    if (right > all.length - 1) {\n      right = all.length - 1;\n      left = Math.max(0, right - span);\n    }\n    if (left < 0) {\n      right -= left;\n      left = 0;\n    }\n    state.range = {start: left, end: right};\n  };\n  canvas.addEventListener("pointerdown", (event) => {\n    if (!canvas._geom || !all.length) return;\n    const px = event.clientX - canvas.getBoundingClientRect().left;\n    const x0 = canvas._geom.x(state.range.start);\n    const x1 = canvas._geom.x(state.range.end);\n    const i = indexAt(event);\n    let mode = "move";\n    if (Math.abs(px - x0) <= 8) mode = "start";\n    else if (Math.abs(px - x1) <= 8) mode = "end";\n    else if (px < x0 || px > x1) mode = "new";\n    drag = {mode, anchor: i, start: state.range.start, end: state.range.end};\n    canvas.setPointerCapture(event.pointerId);\n  });\n  canvas.addEventListener("pointermove", (event) => {\n    if (!drag) return;\n    const i = indexAt(event);\n    if (drag.mode === "start") {\n      state.range.start = Math.max(0, Math.min(i, state.range.end - 4));\n    } else if (drag.mode === "end") {\n      state.range.end = Math.min(all.length - 1, Math.max(i, state.range.start + 4));\n    } else if (drag.mode === "move") {\n      const span = drag.end - drag.start;\n      clampRange(drag.start + (i - drag.anchor), drag.start + (i - drag.anchor) + span);\n    } else {\n      clampRange(Math.min(drag.anchor, i), Math.max(drag.anchor, i));\n    }\n    paint();\n  });\n  const stop = () => { drag = null; };\n  canvas.addEventListener("pointerup", stop);\n  canvas.addEventListener("pointercancel", stop);\n}\n\npaint();\nbindTip(document.getElementById("main"), document.getElementById("tip"));\nbindBrush(document.getElementById("brush"));\nwindow.addEventListener("resize", paint);\n</script>\n</body>\n</html>\n'
