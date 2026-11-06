"""9:16 deck for platform trends. Chrome from screen-pack master."""
from __future__ import annotations
import re
from pathlib import Path
from analyze import TrendReport
from render_slides import build_slides, esc

TOOLS = Path(__file__).resolve().parents[2]
DECK_HTML = TOOLS / "screen-pack" / "src" / "_deck_template.html"
DECK_JS = TOOLS / "screen-pack" / "src" / "_deck_nav.js"
PLOTLY_CDN = "https://cdn.plot.ly/plotly-2.35.2.min.js"

def render_html(*, theme: str, asof: str, report: TrendReport, out_path: Path) -> Path:
    slides = build_slides(theme, asof, report)
    style, nav = _chrome()
    page = _page(theme=theme, asof=asof, style=style, nav=nav, slides=slides)
    out_path = Path(out_path)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(page, encoding="utf-8")
    return out_path

def _chrome() -> tuple[str, str]:
    if not DECK_HTML.is_file() or not DECK_JS.is_file():
        raise RuntimeError("\u627e\u4e0d\u5230 screen-pack \u5f55\u5c4f\u6bcd\u7248")
    template = DECK_HTML.read_text(encoding="utf-8")
    match = re.search(r"<style>(.*?)</style>", template, re.S)
    if not match or "--od-bg:#1e2227" not in match.group(1):
        raise RuntimeError("\u5f55\u5c4f\u6bcd\u7248\u6837\u5f0f\u4e0d\u53ef\u7528")
    return match.group(1), DECK_JS.read_text(encoding="utf-8")

def _page(*, theme, asof, style, nav, slides) -> str:
    body = chr(10).join(slides)
    meta = "\u6293\u53d6 " + asof + " \u00b7 \u5de6\u5f55\u5c4f / \u4e2d\u6587\u6848 / \u53f3\u7ffb\u9875 \u00b7 L \u5de6\u53f3\u5bf9\u8c03"
    extra_css = (
        ".rank-list{margin:0;padding:0;list-style:none;display:flex;flex-direction:column;gap:6px;max-height:100%;overflow:auto}"
        ".rank-list li{display:flex;gap:8px;align-items:flex-start;background:var(--od-panel-2);border:1px solid var(--od-line);border-radius:8px;padding:8px 10px}"
        ".rank-list .n{color:var(--od-cyan);font-variant-numeric:tabular-nums;min-width:1.6em}"
        ".rank-list .t{flex:1;color:#e6e6e6;font-size:1.05rem;line-height:1.35}"
        ".rank-list .m{color:var(--od-muted);font-size:.9rem;white-space:nowrap}"
    )
    return (
        "<!DOCTYPE html>" + chr(10)
        + "<html lang=\"zh-CN\"><head>" + chr(10)
        + "<meta charset=\"utf-8\"/>" + chr(10)
        + "<meta name=\"viewport\" content=\"width=device-width, initial-scale=1, viewport-fit=cover\"/>" + chr(10)
        + "<title>" + esc(theme) + "</title>" + chr(10)
        + "<script src=\"" + PLOTLY_CDN + "\"></script>" + chr(10)
        + "<style>" + style + chr(10) + extra_css + "</style>" + chr(10)
        + "</head><body>" + chr(10)
        + "<div class=\"workbench\">" + chr(10)
        + "  <div class=\"stage-col\">" + chr(10)
        + "    <div class=\"phone\" id=\"phone\">" + chr(10)
        + "      <div class=\"safe-guides\" id=\"safeGuides\" aria-hidden=\"true\">" + chr(10)
        + "        <div class=\"band band-top\"></div>" + chr(10)
        + "        <div class=\"band band-bottom\"></div>" + chr(10)
        + "        <div class=\"band band-left\"></div>" + chr(10)
        + "        <div class=\"band band-right\"></div>" + chr(10)
        + "        <div class=\"label top\">\u9876\u680f \u00b7 \u72b6\u6001/\u9891\u9053</div>" + chr(10)
        + "        <div class=\"label bottom\">\u5e95\u680f\u906e\u6321\u5e26</div>" + chr(10)
        + "        <div class=\"label right\">\u53f3\u7f18</div>" + chr(10)
        + "      </div>" + chr(10)
        + "      <div class=\"deck\" id=\"deck\">" + chr(10)
        + body + chr(10)
        + "      </div>" + chr(10)
        + "    </div>" + chr(10)
        + "  </div>" + chr(10)
        + "  <aside class=\"script-rail\" aria-label=\"script\">" + chr(10)
        + "    <div class=\"rail-head\">" + chr(10)
        + "      <p class=\"eyebrow\">Script</p>" + chr(10)
        + "      <h1>" + esc(theme) + "</h1>" + chr(10)
        + "      <p class=\"meta\">" + esc(meta) + "</p>" + chr(10)
        + "    </div>" + chr(10)
        + "    <div class=\"script-list\" id=\"scriptList\"></div>" + chr(10)
        + "  </aside>" + chr(10)
        + "  <nav class=\"pager\" aria-label=\"pager\">" + chr(10)
        + "    <div class=\"page-label\" id=\"pageLabel\">1/" + str(len(slides)) + "</div>" + chr(10)
        + "    <button type=\"button\" class=\"nav\" id=\"btnPrev\" title=\"prev\">\u2191</button>" + chr(10)
        + "    <button type=\"button\" class=\"nav\" id=\"btnNext\" title=\"next\">\u2193</button>" + chr(10)
        + "    <button type=\"button\" class=\"guide\" id=\"btnGuide\" title=\"safe\">\u5b89\u5168\u533a</button>" + chr(10)
        + "    <button type=\"button\" class=\"flip\" id=\"btnFlip\" title=\"swap layout\">\u5de6\u53f3</button>" + chr(10)
        + "  </nav>" + chr(10)
        + "</div>" + chr(10)
        + "<script>" + chr(10) + nav + chr(10) + "</script>" + chr(10)
        + "</body></html>" + chr(10)
    )
