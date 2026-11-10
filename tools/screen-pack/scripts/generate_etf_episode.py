# -*- coding: utf-8 -*-
"""一期录屏：头部 ETF 九张图，每张一页。工作台用 screen-pack 母版，图用分析页原画法。"""
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

KEEP_DRAW = {"draw", "drawAnomaly", "drawAnomalyBrush", "bindFlowBrush", "drawLineBrush"}
MOUNT_JS = r"""
const charts = __CHARTS__;
function paintOne(spec) {
  const range = spec.state.range;
  const rows = spec.points.slice(range.start, range.end + 1);
  if (!rows.length || !spec.plot.clientWidth) return;
  if (spec.kind === "flow") {
    drawAnomaly(spec.plot, rows, spec.index);
    drawAnomalyBrush(spec.brush, spec.points, range);
  } else {
    draw(spec.plot, rows, spec.index, spec.rightName, spec.rightKey, spec.rightKind);
    drawLineBrush(spec.brush, spec.points, range, spec.rightKey);
  }
}
function mountCharts() {
  document.querySelectorAll(".with-range").forEach((box) => {
    const spec = charts[Number(box.dataset.i)];
    spec.plot = box.querySelector(".plot");
    spec.brush = box.querySelector(".range");
    spec.state = {range: {start: 0, end: Math.max(0, spec.points.length - 1)}};
    const paint = () => paintOne(spec);
    spec.paint = paint;
    paint();
    bindFlowBrush(spec.brush, spec.points, spec.state, paint);
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
        '<div class="slide-tag"><span>%d / %d</span><span>%s</span></div>'
        '<div class="slide-inner"><h2>%s</h2><div class="panel">%s</div></div></section>'
    ) % (
        index,
        index,
        html.escape(title, quote=True),
        script_attr,
        index,
        total,
        html.escape(tag),
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


def main() -> int:
    groups = build_etf_market_share()
    asof = pd.Timestamp(groups[0]["asof"]).strftime("%Y-%m-%d")
    slides, charts = _pages(groups)
    body = "\n".join(
        _slide(i, len(slides), page["title"], page["tag"], page["script"], i - 1)
        for i, page in enumerate(slides, start=1)
    )
    template = _load_deck_template()
    start = template.find('<div class="deck" id="deck">')
    end = template.find("      </div>", template.find('id="slide-end"'))
    if start < 0 or end < 0:
        raise RuntimeError("deck template markers missing")
    html_text = template[: start + len('<div class="deck" id="deck">')] + "\n" + body + "\n" + template[end:]
    html_text = html_text.replace("__NAME__", "头部ETF").replace("__CODE__", "九张图").replace("__ASOF__", asof)
    html_text = html_text.replace('<script src="https://cdn.plot.ly/plotly-2.35.2.min.js"></script>', "")
    data = json.dumps(charts, ensure_ascii=False).replace("<", "\\u003c")
    extra = (
        "<script>\n"
        + _tool_colors(_source_draw_js())
        + "\n"
        + MOUNT_JS.replace("__CHARTS__", data)
        + "\n</script>\n"
    )
    html_text = html_text.replace("</body>", extra + "</body>")
    out = episode_dir(niche="finance", theme="头部ETF持有规模", day=date.today())
    out.mkdir(parents=True, exist_ok=True)
    page_path = out / "index.html"
    page_path.write_text(html_text, encoding="utf-8")
    meta = {
        "theme": "头部ETF持有规模",
        "date": date.today().isoformat(),
        "asof": asof,
        "cache": "cache/etf_market_share_%s" % asof,
        "pages": [page["title"] for page in slides],
        "note": "每张图一页，图用分析页原画法。生成数据仅供参考。",
    }
    (out / "meta.json").write_text(json.dumps(meta, ensure_ascii=False, indent=2), encoding="utf-8")
    print(page_path)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
