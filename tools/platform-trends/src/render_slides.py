"""Slide builders for platform-trends deck."""
from __future__ import annotations
import html, math
import plotly.graph_objects as go
from plotly.offline import plot as plot_offline
from analyze import TrendReport
from normalize import HotItem

PLOT_CONFIG = {"displayModeBar": False, "responsive": True, "scrollZoom": True}
PLATFORM_LABEL = {"bilibili": "\u0042\u7ad9", "weibo": "\u5fae\u535a", "douyin": "\u6296\u97f3"}

def build_slides(theme, asof, report):
    return [cover(theme, asof, report), bilibili_slide(report), weibo_slide(report), douyin_slide(report), overlap_slide(report)]

def _js(parts):
    return chr(10).join(parts)

def cover(theme, asof, report):
    cards = []
    for result in report.results:
        label = PLATFORM_LABEL.get(result.platform, result.platform)
        if result.error:
            value, hint = "\u5931\u8d25", (result.error or "")[:40]
        else:
            value = str(len(result.items))
            hint = "\u4f5c\u54c1" if result.platform == "bilibili" else "\u8bdd\u9898/\u70ed\u8bcd"
        cards.append("<div class=\"card\"><div class=\"label\">" + esc(label) + "</div><div class=\"value\">" + esc(value) + "</div><div class=\"hint\">" + esc(hint) + "</div></div>")
    top_niche = report.summary.get("top_bili_niche") or "\u2014"
    cards.append("<div class=\"card\"><div class=\"label\">\u0042\u7ad9\u5934\u90e8\u5206\u533a</div><div class=\"value\" style=\"font-size:1.35rem\">" + esc(top_niche) + "</div><div class=\"hint\">\u6309\u4f5c\u54c1\u6570\u4f18\u5148</div></div>")
    script = _js([
        "\u8fd9\u9875\u770b\u5e73\u53f0\u4e0a\u4ec0\u4e48\u5728\u706b\uff0c\u4e0d\u662f\u81ea\u5df1\u8d26\u53f7\u540e\u53f0\u3002",
        "\u6293\u53d6\u65f6\u95f4 " + asof + "\u3002\u6210\u529f " + str(report.summary["ok_count"]) + " \u5bb6\uff0c\u5931\u8d25 " + str(report.summary["fail_count"]) + " \u5bb6\u3002",
        "\u0042\u7ad9\u662f\u4f5c\u54c1\u52a0\u5206\u533a\uff1b\u5fae\u535a\u662f\u70ed\u641c\uff1b\u6296\u97f3\u662f\u70ed\u8bcd\u3002",
        "\u70ed\u5ea6\u6570\u503c\u4e0d\u8de8\u5e73\u53f0\u76f8\u52a0\u3002",
        "\u751f\u6210\u6570\u636e\u4ec5\u4f9b\u53c2\u8003\u3002",
    ])
    inner = ("<div class=\"slide-tag\"><span>1 / \u5c01\u9762</span><span>" + esc(asof) + "</span></div>"
             "<div class=\"slide-inner\"><h1 class=\"phone-title\">" + esc(theme) + "</h1>"
             "<p class=\"sub\">\u0042\u7ad9 \u00b7 \u5fae\u535a \u00b7 \u6296\u97f3 \u00b7 \u5c0f\u7ea2\u4e66/\u89c6\u9891\u53f7\u672a\u63a5\u5165</p>"
             "<div class=\"cards\">" + "".join(cards) + "</div></div>")
    return section("slide-cover", "\u5c01\u9762\u8981\u70b9", script, inner, False)


def bilibili_slide(report):
    result = plat(report, "bilibili")
    if result is None or result.error:
        err = result.error if result else "\u672a\u6293\u53d6"
        return section("slide-bili", "\u0042\u7ad9\u4f5c\u54c1", "\u0042\u7ad9\u6293\u53d6\u5931\u8d25\u3002" + chr(10) + err,
            "<div class=\"slide-tag\"><span>2 / \u0042\u7ad9</span><span>\u5931\u8d25</span></div><div class=\"slide-inner\"><h2>\u0042\u7ad9\u70ed\u95e8\u4f5c\u54c1</h2><div class=\"disclaimer\">" + esc(err) + "</div></div>", False)
    niches = report.bilibili_niches[:8]
    fig = go.Figure(go.Bar(x=[r["niche"] for r in niches], y=[r["works"] for r in niches], marker_color="#61afef",
        customdata=[[fmt_count(r["views"]), fmt_count(r["likes"])] for r in niches],
        hovertemplate="%{x}<br>\u4f5c\u54c1 %{y}<br>\u64ad\u653e %{customdata[0]}<br>\u70b9\u8d5e %{customdata[1]}<extra></extra>"))
    dress(fig)
    chart = plot_offline(fig, output_type="div", include_plotlyjs=False, config=PLOT_CONFIG)
    top_niche = niches[0]["niche"] if niches else "\u2014"
    script = _js(["\u0042\u7ad9\u8fd9\u4e00\u9875\u770b\u70ed\u95e8\u4f5c\u54c1\u548c\u5206\u533a\u3002", "\u5934\u90e8\u5206\u533a\u662f " + top_niche + "\u3002",
        "\u67f1\u9ad8\u662f\u5206\u533a\u4f5c\u54c1\u6570\uff0c\u60ac\u6d6e\u770b\u64ad\u653e\u548c\u70b9\u8d5e\u5408\u8ba1\u3002", "\u4e0b\u9762\u5217\u51fa\u699c\u4e0a\u524d\u51e0\u6761\u4f5c\u54c1\u6807\u9898\u3002", "\u53ea\u63cf\u8ff0\u8fd9\u6279\u516c\u5f00\u699c\uff0c\u4e0d\u505a\u64cd\u4f5c\u5efa\u8bae\u3002"])
    inner = ("<div class=\"slide-tag\"><span>2 / \u0042\u7ad9</span><span>" + str(len(result.items)) + " \u6761</span></div>"
             "<div class=\"slide-inner\"><h2>\u0042\u7ad9\u70ed\u95e8 \u00b7 \u5206\u533a</h2>"
             "<div class=\"panel\"><div class=\"note\">\u67f1=\u5206\u533a\u4f5c\u54c1\u6570</div><div class=\"chart-box\">" + chart + "</div></div>"
             "<ul class=\"rank-list\" style=\"max-height:28%;margin-top:6px\">" + rank_list(result.items[:5], "\u64ad") + "</ul></div>")
    return section("slide-bili", "\u0042\u7ad9\u4f5c\u54c1", script, inner, True)

def weibo_slide(report):
    result = plat(report, "weibo")
    if result is None or result.error:
        err = result.error if result else "\u672a\u6293\u53d6"
        return section("slide-weibo", "\u5fae\u535a\u70ed\u641c", "\u5fae\u535a\u6293\u53d6\u5931\u8d25\u3002" + chr(10) + err,
            "<div class=\"slide-tag\"><span>3 / \u5fae\u535a</span><span>\u5931\u8d25</span></div><div class=\"slide-inner\"><h2>\u5fae\u535a\u70ed\u641c</h2><div class=\"disclaimer\">" + esc(err) + "</div></div>", False)
    niche_bits = "\u3001".join(r["niche"] for r in report.weibo_niches[:4]) or "\u591a\u6570\u6761\u76ee\u65e0\u5206\u7c7b"
    script = _js(["\u5fae\u535a\u8fd9\u4e00\u9875\u770b\u70ed\u641c\u8bdd\u9898\u3002", "\u5206\u7c7b\u5206\u5e03\uff1a" + niche_bits + "\u3002", "\u70ed\u5ea6\u662f\u5e73\u53f0\u539f\u503c\uff0c\u4e0d\u548c\u6296\u97f3\u76f8\u52a0\u3002", "\u53ea\u8bfb\u699c\uff0c\u4e0d\u7ed9\u7ed3\u8bba\u3002"])
    inner = ("<div class=\"slide-tag\"><span>3 / \u5fae\u535a</span><span>" + str(len(result.items)) + " \u6761</span></div>"
             "<div class=\"slide-inner\"><h2>\u5fae\u535a\u70ed\u641c</h2><ul class=\"rank-list\">" + rank_list(result.items[:12], "\u70ed") + "</ul></div>")
    return section("slide-weibo", "\u5fae\u535a\u70ed\u641c", script, inner, False)


def douyin_slide(report):
    result = plat(report, "douyin")
    if result is None or result.error:
        err = result.error if result else "\u672a\u6293\u53d6"
        return section("slide-douyin", "\u6296\u97f3\u70ed\u8bcd", "\u6296\u97f3\u6293\u53d6\u5931\u8d25\u3002" + chr(10) + err,
            "<div class=\"slide-tag\"><span>4 / \u6296\u97f3</span><span>\u5931\u8d25</span></div><div class=\"slide-inner\"><h2>\u6296\u97f3\u70ed\u8bcd</h2><div class=\"disclaimer\">" + esc(err) + "</div></div>", False)
    top = result.items[:10]
    fig = go.Figure(go.Bar(x=[it.title[:10] for it in top][::-1], y=[(it.heat or 0) for it in top][::-1],
        orientation="h", marker_color="#56b6c2", hovertemplate="%{x}<br>\u70ed\u5ea6 %{y:,.0f}<extra></extra>"))
    dress(fig)
    chart = plot_offline(fig, output_type="div", include_plotlyjs=False, config=PLOT_CONFIG)
    first = top[0].title if top else "\u2014"
    script = _js(["\u6296\u97f3\u8fd9\u4e00\u9875\u662f\u70ed\u8bcd\u699c\uff0c\u4e0d\u662f\u4f5c\u54c1\u5217\u8868\u3002", "\u5f53\u524d\u7b2c\u4e00\u662f " + first + "\u3002",
        "\u8d5b\u9053\u6807\u6210\u672a\u6807\u6ce8\uff0c\u56e0\u4e3a\u516c\u5f00\u70ed\u8bcd\u63a5\u53e3\u6ca1\u6709\u5206\u533a\u3002", "\u70ed\u5ea6\u662f\u5e73\u53f0\u539f\u503c\u3002"])
    inner = ("<div class=\"slide-tag\"><span>4 / \u6296\u97f3</span><span>" + str(len(result.items)) + " \u6761</span></div>"
             "<div class=\"slide-inner\"><h2>\u6296\u97f3\u70ed\u8bcd</h2>"
             "<div class=\"panel\"><div class=\"note\">\u70ed\u8bcd \u00b7 \u65e0\u5206\u533a</div><div class=\"chart-box\">" + chart + "</div></div></div>")
    return section("slide-douyin", "\u6296\u97f3\u70ed\u8bcd", script, inner, True)

def overlap_slide(report):
    overlaps = report.overlaps[:6]
    if overlaps:
        blocks = []
        spoken = ["\u8de8\u5e73\u53f0\u5bf9\u7167\u53ea\u770b\u6807\u9898\u662f\u5426\u76f8\u8fd1\uff0c\u4e0d\u628a\u70ed\u5ea6\u52a0\u603b\u3002"]
        for row in overlaps:
            plats = " \u00d7 ".join(PLATFORM_LABEL.get(p, p) for p in row["platforms"])
            titles = " / ".join(row["titles"][p] for p in row["platforms"])
            blocks.append("<p class=\"sub\"><b>" + esc(plats) + "</b> \u00b7 " + esc(titles) + "</p>")
            spoken.append(plats + "\uff1a" + titles + "\u3002")
        spoken.append("\u5c0f\u7ea2\u4e66\u548c\u89c6\u9891\u53f7\u672c\u671f\u672a\u63a5\u5165\u3002")
        spoken.append("\u751f\u6210\u6570\u636e\u4ec5\u4f9b\u53c2\u8003\uff0c\u4e0d\u6784\u6210\u4efb\u4f55\u51b3\u7b56\u4f9d\u636e\u3002")
        extras = chr(10).join(blocks)
    else:
        extras = "<p class=\"sub\">\u8fd9\u6279\u699c\u91cc\u6ca1\u6709\u660e\u663e\u8de8\u5e73\u53f0\u91cd\u5408\u6807\u9898\u3002</p>"
        spoken = ["\u8fd9\u6279\u699c\u91cc\u6ca1\u6709\u660e\u663e\u8de8\u5e73\u53f0\u91cd\u5408\u6807\u9898\u3002", "\u5c0f\u7ea2\u4e66\u548c\u89c6\u9891\u53f7\u672c\u671f\u672a\u63a5\u5165\u3002", "\u751f\u6210\u6570\u636e\u4ec5\u4f9b\u53c2\u8003\uff0c\u4e0d\u6784\u6210\u4efb\u4f55\u51b3\u7b56\u4f9d\u636e\u3002"]
    inner = ("<div class=\"slide-tag\"><span>5 / \u5bf9\u7167</span><span>" + str(len(report.overlaps)) + " \u7ec4</span></div>"
             "<div class=\"slide-inner\"><h2>\u8de8\u5e73\u53f0\u91cd\u5408</h2>"
             "<div class=\"disclaimer\">\u751f\u6210\u6570\u636e\u4ec5\u4f9b\u53c2\u8003\uff0c\u4e0d\u6784\u6210\u4efb\u4f55\u51b3\u7b56\u4f9d\u636e\u3002\u70ed\u5ea6\u4e0d\u8de8\u5e73\u53f0\u6362\u7b97\u3002\u516c\u5f00\u63a5\u53e3\u53ef\u80fd\u98ce\u63a7\u6216\u53d8\u66f4\u3002\u5c0f\u7ea2\u4e66 / \u89c6\u9891\u53f7\u672a\u63a5\u5165\u3002</div>"
             + extras + "<p class=\"sub\">\u5feb\u6377\u952e\uff1a\u7a7a\u683c/\u2193 \u4e0b\u4e00\u9875 \u00b7 \u2191 \u4e0a\u4e00\u9875 \u00b7 G \u5b89\u5168\u533a</p></div>")
    return section("slide-end", "\u8de8\u5e73\u53f0\u5bf9\u7167", _js(spoken), inner, False)

def plat(report, name):
    for result in report.results:
        if result.platform == name:
            return result
    return None

def rank_list(items, heat_label):
    rows = []
    for item in items:
        rank = item.rank if item.rank is not None else "-"
        meta_bits = []
        if item.author:
            meta_bits.append(item.author)
        if item.heat is not None:
            meta_bits.append(heat_label + " " + fmt_count(item.heat))
        if item.niche and item.niche != "\u672a\u6807\u6ce8":
            meta_bits.append(item.niche)
        meta = " \u00b7 ".join(meta_bits)
        rows.append("<li><span class=\"n\">" + esc(rank) + "</span><span class=\"t\">" + esc(item.title) + "</span><span class=\"m\">" + esc(meta) + "</span></li>")
    return "".join(rows)

def dress(fig):
    fig.update_layout(template="plotly_dark", paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
        margin=dict(l=40, r=16, t=24, b=36), font=dict(color="#abb2bf", size=12), showlegend=False,
        hoverlabel=dict(bgcolor="#282c34", bordercolor="#3e4451", font=dict(color="#abb2bf", size=12)))
    fig.update_xaxes(automargin=True, showgrid=False, title=None, tickfont=dict(size=11, color="#abb2bf"))
    fig.update_yaxes(automargin=True, showgrid=True, gridcolor="rgba(62,68,81,.35)", zeroline=False,
        title=None, tickfont=dict(size=11, color="#abb2bf"), rangemode="tozero")

def fmt_count(value):
    if value is None or (isinstance(value, float) and math.isnan(value)):
        return "-"
    number = float(value)
    if abs(number) >= 10000:
        return (("%.2f" % (number / 10000)).rstrip("0").rstrip(".")) + "\u4e07"
    if abs(number - round(number)) < 1e-6:
        return format(int(round(number)), ",")
    return "%.1f" % number

def esc(value):
    return html.escape(str(value), quote=True)

def esc_script(value):
    return esc(value).replace(chr(10), "&#10;")

def section(sid, title, script, inner, chart):
    kind = "slide slide-chart" if chart else "slide"
    return "<section class=\"" + kind + "\" id=\"" + sid + "\" data-title=\"" + esc(title) + "\" data-script=\"" + esc_script(script) + "\">" + inner + "</section>"
