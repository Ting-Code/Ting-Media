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


def write_valuation_group_page(
    title: str,
    items: list[dict],
    out_dir: Path,
    *,
    lead: str | None = None,
    heading: str | None = None,
) -> Path:
    """Write one landscape HTML for many stocks: table + charts + right-side nav.

    Each item: name, code, series (DataFrame), summary (dict), optional weight, optional note.
    """
    out_dir = Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    rows = []
    asofs = []
    for item in items:
        summary = dict(item.get("summary") or {})
        series = item.get("series")
        name = item.get("name") or summary.get("name") or ""
        code = str(item.get("code") or summary.get("code") or "")
        weight = item.get("weight")
        points = [] if series is None or series.empty else _points(series)
        pe = _num(summary.get("pe"), 2)
        pe_points = 0
        if series is not None and not series.empty and "pe" in series.columns:
            pe_points = int(series["pe"].notna().sum())
        note = item.get("note")
        if not note and pe is None:
            note = "当前 PE 留空：上一季单季盈利小于或等于 0。"
        if pe_points < 5:
            extra = "有效 PE 点很少，历史分位参考意义有限。"
            note = f"{note} {extra}".strip() if note else extra
        rows.append(
            {
                "name": name,
                "code": code,
                "weight": None if weight is None else float(weight),
                "asof": summary.get("asof") or "—",
                "price": _num(summary.get("price"), 2),
                "pe": pe,
                "pe_percentile": None if pe is None else _num(summary.get("pe_percentile"), 1),
                "pb": _num(summary.get("pb"), 2),
                "pb_percentile": _num(summary.get("pb_percentile"), 1),
                "report_date": summary.get("report_date") or "—",
                "market": str(summary.get("market") or "").lower(),
                "currency_price": str(summary.get("currency_price") or "").upper(),
                "points": points,
                "pe_points": pe_points,
                "note": note,
                "summary": summary,
            }
        )
        if summary.get("asof"):
            asofs.append(str(summary["asof"])[:10])
    asof = max(asofs) if asofs else "—"
    markets = {r["market"] or ("hk" if r["currency_price"] == "HKD" else "a") for r in rows}
    if markets == {"hk"}:
        page_lead = _HK_LEAD.replace("__ASOF__", _esc(asof)).replace(
            "__REPORT__", "各股标注的报告期"
        )
    elif "hk" in markets and "a" in markets:
        page_lead = (
            f"截至 {asof}。A 股用上一季单季扣非净利润年化（×4）配该季末不复权收盘价；"
            "港股用上一季单季股东应占溢利对应的基本每股盈利年化（×4），"
            "配该季末不复权港股收盘价，再按当日港币人民币中间价折成人民币计算 PE/PB。"
            "当季未结束时用最新完整收盘。绿线股价：港股为港元，A 股为人民币。"
        )
    else:
        page_lead = _A_LEAD.replace("__ASOF__", _esc(asof)).replace(
            "__REPORT__", "各股标注的报告期"
        )
    if lead:
        page_lead = lead.rstrip() + " " + page_lead

    weighted_bits = []
    w_pairs = [(r["weight"], r["pe"]) for r in rows if r["weight"] is not None and r["pe"] is not None]
    if w_pairs:
        wsum = sum(w for w, _ in w_pairs)
        wavg = sum(w * p for w, p in w_pairs) / wsum
        names = "、".join(r["name"] for r in rows if r["weight"] is not None and r["pe"] is not None)
        weighted_bits.append(
            f"按给定权重、只对当前有 PE 的股票（{ _esc(names) }）加权平均约为 {_fmt(wavg, 2)}。"
            "这不是组合或基金本身的估值，权重若来自定期报告也不一定是最新的，仅供对照。"
        )

    nav_links = []
    table_rows = []
    sections = []
    has_weight = any(r["weight"] is not None for r in rows)
    for i, r in enumerate(rows, 1):
        sid = f"stock-{_esc(r['code'])}"
        pe_flag = "<sup>*</sup>" if r["note"] else ""
        weight_cell = f"<td class='num'>{r['weight']:.2f}%</td>" if has_weight else ""
        table_rows.append(
            "<tr>"
            f"<td>{i}</td>"
            f"<td><a href=\"#{sid}\">{_esc(r['name'])}</a></td>"
            f"<td>{_esc(r['code'])}</td>"
            f"{weight_cell}"
            f"<td class='num'>{_esc(_fmt(r['price']))}</td>"
            f"<td class='num'>{_esc(_fmt(r['pe']))}{pe_flag}</td>"
            f"<td class='num'>{_esc(_fmt(r['pe_percentile'], 1, '%'))}</td>"
            f"<td class='num'>{_esc(_fmt(r['pb']))}</td>"
            f"<td class='num'>{_esc(_fmt(r['pb_percentile'], 1, '%'))}</td>"
            f"<td>{_esc(r['report_date'])}</td>"
            "</tr>"
        )
        nav_label = _esc(r["name"])
        nav_pe = _esc(_fmt(r["pe"]))
        nav_links.append(
            f'<a href="#{sid}" data-target="{sid}"><span class="nav-name">{nav_label}</span>'
            f'<span class="nav-meta">{_esc(r["code"])}　PE {nav_pe}</span></a>'
        )
        note_html = f'<p class="note">{_esc(r["note"])}</p>' if r["note"] else ""
        hk = r["market"] == "hk" or r["currency_price"] == "HKD"
        price_unit = "港元" if hk else "元"
        payload = json.dumps(
            {"points": r["points"], "pe_now": r["pe"], "name": r["name"], "code": r["code"]},
            ensure_ascii=False,
        ).replace("<", "\\u003c")
        weight_h = f"　占净值 {r['weight']:.2f}%" if r["weight"] is not None else ""
        sections.append(
            f"""
<section class="stock" id="{sid}">
  <h2>{i}. {_esc(r['name'])} {_esc(r['code'])}{weight_h}</h2>
  <ul class="stats">
    <li>股价 <b>{_esc(_fmt(r['price']))}</b> {price_unit}</li>
    <li>PE <b>{_esc(_fmt(r['pe']))}</b> · 历史分位 {_esc(_fmt(r['pe_percentile'], 1, '%'))}</li>
    <li>PB <b>{_esc(_fmt(r['pb']))}</b> · 历史分位 {_esc(_fmt(r['pb_percentile'], 1, '%'))}</li>
    <li>报告期 {_esc(r['report_date'])}</li>
  </ul>
  {note_html}
  <p class="axis">红线是 PE，蓝线是 PB，绿线是季度末股价。三条线各用自己的纵轴，按当前选中区间各自拉满，不共用刻度。纵轴数字隐藏，鼠标移到点上看真值。缺值的季度断开。红色虚线是当前 PE。</p>
  <ul class="legend">
    <li><i class="pe"></i>PE</li>
    <li><i class="pb"></i>PB</li>
    <li><i class="price"></i>股价</li>
    <li><i class="now"></i>当前 PE</li>
  </ul>
  <div class="chart"><canvas class="main"></canvas></div>
  <div class="brush"><canvas class="brush-canvas"></canvas></div>
  <p class="axis range"></p>
  <div class="tip">鼠标移到图上看 PE、PB 和股价。下方色带拖动选区，拖两端改范围。</div>
  <script type="application/json" class="pack">{payload}</script>
</section>
"""
        )

    weight_th = "<th>占净值</th>" if has_weight else ""
    weighted_html = (
        f'<p class="lead" style="margin-top:12px">{weighted_bits[0]}</p>' if weighted_bits else ""
    )
    footer = (
        "单季盈利小于或等于 0 时，该季 PE 留空。生成数据仅供参考，不构成投资建议。"
    )
    page_title = heading or title
    html = f"""<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{_esc(page_title)}</title>
<style>
  body {{ margin: 0; background: #f3f4f6; color: #1a1a1a; font-family: "Microsoft YaHei", "PingFang SC", sans-serif; }}
  main {{ max-width: 1080px; margin: 0 auto; padding: 32px 236px 56px 20px; }}
  h1 {{ font-size: 26px; line-height: 1.3; margin: 0 0 8px; }}
  h2 {{ font-size: 20px; margin: 0 0 8px; }}
  .lead, .axis, .note {{ margin: 0; color: #4b4b4b; font-size: 14px; line-height: 1.7; }}
  .note {{ margin-top: 8px; color: #7a3b00; }}
  .summary {{ background: #fff; border: 1px solid #e3e3e3; margin-top: 18px; padding: 16px; overflow-x: auto; }}
  table {{ width: 100%; border-collapse: collapse; font-size: 14px; }}
  th, td {{ padding: 8px 10px; border-bottom: 1px solid #eee; text-align: left; white-space: nowrap; }}
  th {{ color: #555; font-weight: 600; }}
  td.num {{ text-align: right; font-variant-numeric: tabular-nums; }}
  tr:hover {{ background: #f7f7f7; }}
  a {{ color: #1d4e89; text-decoration: none; }}
  a:hover {{ text-decoration: underline; }}
  .stock {{ background: #fff; border: 1px solid #e3e3e3; margin-top: 18px; padding: 16px 16px 8px; scroll-margin-top: 16px; }}
  .stats {{ display: flex; flex-wrap: wrap; gap: 8px 22px; margin: 12px 0 8px; padding: 0; list-style: none; font-size: 15px; }}
  .stats b {{ font-weight: 650; }}
  .legend {{ display: flex; flex-wrap: wrap; gap: 8px 18px; margin: 10px 0 6px; padding: 0; list-style: none; font-size: 13px; color: #333; }}
  .legend i {{ display: inline-block; width: 12px; height: 3px; margin-right: 6px; vertical-align: middle; }}
  .legend .pe {{ background: #c0392b; }}
  .legend .pb {{ background: #1d4e89; }}
  .legend .price {{ background: #1c7c4a; }}
  .legend .now {{ background: #c0392b; height: 0; border-top: 2px dashed #c0392b; }}
  .chart {{ position: relative; }}
  canvas {{ width: 100%; display: block; cursor: crosshair; }}
  .chart canvas {{ height: 420px; }}
  .brush canvas {{ height: 72px; cursor: ew-resize; }}
  .tip {{ min-height: 20px; margin: 2px 0 8px; color: #333; font-size: 12px; }}
  footer {{ margin-top: 16px; color: #666; font-size: 12px; line-height: 1.7; }}
  nav.toc {{ position: fixed; top: 24px; right: 16px; width: 200px; max-height: calc(100vh - 48px); overflow: auto; background: #fff; border: 1px solid #e3e3e3; padding: 10px 0; z-index: 20; }}
  nav.toc .nav-title {{ margin: 0 12px 8px; color: #666; font-size: 12px; }}
  nav.toc a {{ display: block; padding: 7px 12px; color: #1a1a1a; text-decoration: none; border-left: 3px solid transparent; line-height: 1.35; }}
  nav.toc a:hover {{ background: #f7f7f7; text-decoration: none; }}
  nav.toc a.active {{ border-left-color: #1d4e89; background: #f3f6fa; }}
  nav.toc .nav-name {{ display: block; font-size: 13px; }}
  nav.toc .nav-meta {{ display: block; color: #666; font-size: 11px; margin-top: 2px; }}
  @media (max-width: 1180px) {{
    main {{ padding: 72px 16px 56px; }}
    nav.toc {{ top: 0; right: 0; left: 0; width: auto; max-height: none; display: flex; overflow-x: auto; padding: 0; border-left: 0; border-right: 0; }}
    nav.toc .nav-title {{ display: none; }}
    nav.toc a {{ flex: 0 0 auto; border-left: none; border-bottom: 3px solid transparent; white-space: nowrap; }}
    nav.toc a.active {{ border-bottom-color: #1d4e89; background: #f3f6fa; }}
  }}
</style>
</head>
<body>
<nav class="toc" id="toc">
  <p class="nav-title">图表目录</p>
  {''.join(nav_links)}
</nav>
<main>
  <h1>{_esc(page_title)}</h1>
  <p class="lead">{page_lead}</p>
  <div class="summary">
    <table>
      <thead>
        <tr>
          <th>#</th><th>名称</th><th>代码</th>{weight_th}<th>股价</th>
          <th>PE</th><th>PE分位</th><th>PB</th><th>PB分位</th><th>报告期</th>
        </tr>
      </thead>
      <tbody>
        {''.join(table_rows)}
      </tbody>
    </table>
    {weighted_html}
  </div>
  {''.join(sections)}
  <footer>{footer}</footer>
</main>
<script>
function finite(values) {{
  return values.filter((v) => v != null && Number.isFinite(v));
}}
function padded(values, pad) {{
  const nums = finite(values);
  if (!nums.length) return null;
  let lo = Math.min(...nums);
  let hi = Math.max(...nums);
  if (lo === hi) {{
    const delta = Math.abs(lo) * 0.1 || 1;
    return {{lo: lo - delta, hi: hi + delta}};
  }}
  const span = hi - lo;
  return {{lo: lo - span * pad, hi: hi + span * pad}};
}}
function bindChart(section) {{
  const pack = JSON.parse(section.querySelector(".pack").textContent);
  const all = pack.points || [];
  const peNow = pack.pe_now;
  const state = {{range: {{start: 0, end: Math.max(0, all.length - 1)}}}};
  const main = section.querySelector("canvas.main");
  const brush = section.querySelector("canvas.brush-canvas");
  const tip = section.querySelector(".tip");
  const label = section.querySelector(".range");
  const slice = () => all.slice(state.range.start, state.range.end + 1);

  function drawMain(canvas, points) {{
    const dpr = window.devicePixelRatio || 1;
    const width = canvas.clientWidth;
    const height = canvas.clientHeight;
    canvas.width = Math.max(1, Math.floor(width * dpr));
    canvas.height = Math.max(1, Math.floor(height * dpr));
    const ctx = canvas.getContext("2d");
    ctx.setTransform(dpr, 0, 0, dpr, 0, 0);
    const pad = {{l: 28, r: 28, t: 18, b: 34}};
    const plotW = width - pad.l - pad.r;
    const plotH = height - pad.t - pad.b;
    const n = points.length;
    const peRange = padded(points.map((p) => p.pe), 0.08);
    const pbRange = padded(points.map((p) => p.pb), 0.08);
    const priceRange = padded(points.map((p) => p.price), 0.08);
    if (peNow != null && peRange) {{
      peRange.lo = Math.min(peRange.lo, peNow);
      peRange.hi = Math.max(peRange.hi, peNow);
    }}
    const x = (i) => pad.l + (n < 2 ? plotW / 2 : (i / (n - 1)) * plotW);
    const yOf = (range, v) => pad.t + (range.hi - v) / (range.hi - range.lo || 1) * plotH;
    ctx.clearRect(0, 0, width, height);
    ctx.strokeStyle = "#ececec";
    ctx.lineWidth = 1;
    for (let i = 0; i <= 4; i++) {{
      const y = pad.t + (plotH * i) / 4;
      ctx.beginPath();
      ctx.moveTo(pad.l, y);
      ctx.lineTo(width - pad.r, y);
      ctx.stroke();
    }}
    if (peNow != null && peRange) {{
      const y = yOf(peRange, peNow);
      ctx.setLineDash([6, 5]);
      ctx.strokeStyle = "#c0392b";
      ctx.beginPath();
      ctx.moveTo(pad.l, y);
      ctx.lineTo(width - pad.r, y);
      ctx.stroke();
      ctx.setLineDash([]);
      ctx.fillStyle = "#c0392b";
      ctx.font = "12px Microsoft YaHei, sans-serif";
      ctx.textAlign = "left";
      ctx.fillText("当前 PE " + peNow.toFixed(1), pad.l + 4, Math.max(pad.t + 12, y - 6));
    }}
    const series = [
      {{key: "pe", color: "#c0392b", range: peRange}},
      {{key: "pb", color: "#1d4e89", range: pbRange}},
      {{key: "price", color: "#1c7c4a", range: priceRange}},
    ];
    series.forEach((item) => {{
      if (!item.range) return;
      ctx.strokeStyle = item.color;
      ctx.fillStyle = item.color;
      ctx.lineWidth = 2;
      let started = false;
      ctx.beginPath();
      points.forEach((p, i) => {{
        const v = p[item.key];
        if (v == null || !Number.isFinite(v)) {{ started = false; return; }}
        const cx = x(i);
        const cy = yOf(item.range, v);
        if (!started) {{ ctx.moveTo(cx, cy); started = true; }}
        else ctx.lineTo(cx, cy);
      }});
      ctx.stroke();
      points.forEach((p, i) => {{
        const v = p[item.key];
        if (v == null || !Number.isFinite(v)) return;
        ctx.beginPath();
        ctx.arc(x(i), yOf(item.range, v), 3.2, 0, Math.PI * 2);
        ctx.fill();
      }});
    }});
    ctx.fillStyle = "#666";
    ctx.font = "12px Microsoft YaHei, sans-serif";
    if (points.length) {{
      ctx.textAlign = "left";
      ctx.fillText(points[0].date.slice(0, 7), pad.l, height - 8);
      ctx.textAlign = "right";
      ctx.fillText(points[points.length - 1].date.slice(0, 7), width - pad.r, height - 8);
    }}
    canvas._geom = {{n, x, pad, plotW, plotH}};
  }}

  function drawBrush(canvas, points, range) {{
    const dpr = window.devicePixelRatio || 1;
    const width = canvas.clientWidth;
    const height = canvas.clientHeight;
    canvas.width = Math.max(1, Math.floor(width * dpr));
    canvas.height = Math.max(1, Math.floor(height * dpr));
    const ctx = canvas.getContext("2d");
    ctx.setTransform(dpr, 0, 0, dpr, 0, 0);
    const pad = {{l: 28, r: 28, t: 8, b: 18}};
    const plotW = width - pad.l - pad.r;
    const plotH = height - pad.t - pad.b;
    const n = points.length;
    const peRange = padded(points.map((p) => p.pe), 0.08) || {{lo: 0, hi: 1}};
    const x = (i) => pad.l + (n < 2 ? plotW / 2 : (i / (n - 1)) * plotW);
    const y = (v) => pad.t + (peRange.hi - v) / (peRange.hi - peRange.lo || 1) * plotH;
    ctx.clearRect(0, 0, width, height);
    ctx.strokeStyle = "#c0392b";
    ctx.lineWidth = 1.2;
    let started = false;
    ctx.beginPath();
    points.forEach((p, i) => {{
      if (p.pe == null || !Number.isFinite(p.pe)) {{ started = false; return; }}
      const cx = x(i);
      const cy = y(p.pe);
      if (!started) {{ ctx.moveTo(cx, cy); started = true; }}
      else ctx.lineTo(cx, cy);
    }});
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
    if (points.length) {{
      ctx.textAlign = "left";
      ctx.fillText(points[0].date.slice(0, 7), pad.l, height - 4);
      ctx.textAlign = "right";
      ctx.fillText(points[points.length - 1].date.slice(0, 7), width - pad.r, height - 4);
    }}
    canvas._geom = {{n, x, pad}};
  }}

  function paint() {{
    const points = slice();
    drawMain(main, points);
    drawBrush(brush, all, state.range);
    if (points.length) {{
      label.textContent = "显示 " + points[0].date + " 至 " + points[points.length - 1].date + "，共 " + points.length + " 个季度。主图按选中区间重新定三条纵轴。";
    }} else {{
      label.textContent = "没有可画的季度点。";
    }}
  }}

  main.addEventListener("mousemove", (event) => {{
    const geom = main._geom;
    const points = slice();
    if (!geom || !points.length) return;
    const px = event.clientX - main.getBoundingClientRect().left;
    let nearest = 0, best = Infinity;
    points.forEach((_, i) => {{
      const dist = Math.abs(geom.x(i) - px);
      if (dist < best) {{ best = dist; nearest = i; }}
    }});
    const p = points[nearest];
    const pe = p.pe == null ? "—" : p.pe.toFixed(2);
    const pb = p.pb == null ? "—" : p.pb.toFixed(2);
    const price = p.price == null ? "—" : p.price.toFixed(2);
    const flag = p.incomplete ? " · 当季未结束，用最新收盘" : "";
    tip.textContent = p.date + "  PE " + pe + "  PB " + pb + "  股价 " + price + flag;
  }});

  let drag = null;
  const indexAt = (event) => {{
    const geom = brush._geom;
    const px = event.clientX - brush.getBoundingClientRect().left;
    let nearest = 0, best = Infinity;
    for (let i = 0; i < geom.n; i++) {{
      const dist = Math.abs(geom.x(i) - px);
      if (dist < best) {{ best = dist; nearest = i; }}
    }}
    return nearest;
  }};
  const clampRange = (start, end) => {{
    const span = Math.max(4, end - start);
    let left = start, right = start + span;
    if (right > all.length - 1) {{ right = all.length - 1; left = Math.max(0, right - span); }}
    if (left < 0) {{ right -= left; left = 0; }}
    state.range = {{start: left, end: right}};
  }};
  brush.addEventListener("pointerdown", (event) => {{
    if (!brush._geom || !all.length) return;
    const px = event.clientX - brush.getBoundingClientRect().left;
    const x0 = brush._geom.x(state.range.start);
    const x1 = brush._geom.x(state.range.end);
    const i = indexAt(event);
    let mode = "move";
    if (Math.abs(px - x0) <= 8) mode = "start";
    else if (Math.abs(px - x1) <= 8) mode = "end";
    else if (px < x0 || px > x1) mode = "new";
    drag = {{mode, anchor: i, start: state.range.start, end: state.range.end}};
    brush.setPointerCapture(event.pointerId);
  }});
  brush.addEventListener("pointermove", (event) => {{
    if (!drag) return;
    const i = indexAt(event);
    if (drag.mode === "start") state.range.start = Math.max(0, Math.min(i, state.range.end - 4));
    else if (drag.mode === "end") state.range.end = Math.min(all.length - 1, Math.max(i, state.range.start + 4));
    else if (drag.mode === "move") {{
      const span = drag.end - drag.start;
      clampRange(drag.start + (i - drag.anchor), drag.start + (i - drag.anchor) + span);
    }} else clampRange(Math.min(drag.anchor, i), Math.max(drag.anchor, i));
    paint();
  }});
  const stop = () => {{ drag = null; }};
  brush.addEventListener("pointerup", stop);
  brush.addEventListener("pointercancel", stop);
  paint();
  window.addEventListener("resize", paint);
}}

document.querySelectorAll("section.stock").forEach(bindChart);

(function bindNav() {{
  const nav = document.getElementById("toc");
  const links = [...nav.querySelectorAll("a[data-target]")];
  const sections = links.map((a) => document.getElementById(a.dataset.target)).filter(Boolean);
  links.forEach((a) => {{
    a.addEventListener("click", (event) => {{
      event.preventDefault();
      const target = document.getElementById(a.dataset.target);
      if (target) target.scrollIntoView({{behavior: "smooth", block: "start"}});
    }});
  }});
  const sync = () => {{
    let current = sections[0];
    for (const section of sections) {{
      if (section.getBoundingClientRect().top <= 88) current = section;
    }}
    links.forEach((a) => a.classList.toggle("active", current && a.dataset.target === current.id));
  }};
  window.addEventListener("scroll", sync, {{passive: true}});
  sync();
}})();
</script>
</body>
</html>
"""
    path = out_dir / "index.html"
    path.write_text(html, encoding="utf-8")
    meta = {
        "title": page_title,
        "asof": asof,
        "items": [
            {k: v for k, v in r.items() if k not in {"points", "summary"}}
            for r in rows
        ],
    }
    (out_dir / "summary.json").write_text(
        json.dumps(meta, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    return path
