# -*- coding: utf-8 -*-
# Sector analysis episode: cover + one page per sector + end.
from __future__ import annotations

import html as html_lib
import json
import shutil
from datetime import datetime
from pathlib import Path

import pandas as pd
import plotly.graph_objects as go
from plotly.offline import plot as plot_offline
from plotly.subplots import make_subplots

ROOT = Path(__file__).resolve().parents[3]
ANALYSIS_SRC = ROOT / "tools/stock-analysis/src"
EP_DATE = "2026-10-27"
OUT = ROOT / "episodes/finance" / (EP_DATE + "_板块分析")
OLD = ROOT / "episodes/finance" / (EP_DATE + "_恒生科技板块PE")
CACHE = OUT / "cache"


def _fmt(v, nd=2, suffix=""):
    if v is None or (isinstance(v, float) and pd.isna(v)):
        return "-"
    return ("%%.%df" % nd) % v + suffix


def percentile(s, v):
    s = s.dropna()
    if s.empty or v is None or pd.isna(v):
        return None
    return float((s <= v).mean() * 100)


def month_end_close(daily, day):
    sub = daily[daily["date"] <= day]
    if sub.empty:
        return None
    row = sub.iloc[-1]
    return pd.Timestamp(row["date"]), float(row["close"])


def ensure_cache_from_old():
    CACHE.mkdir(parents=True, exist_ok=True)
    src = OLD / "cache"
    if not src.exists():
        return
    for p in src.iterdir():
        dest = CACHE / p.name
        if not dest.exists():
            shutil.copy2(p, dest)


def load_hstech_sector():
    val_path = CACHE / "sector_valuation.csv"
    idx_path = CACHE / "index_daily.csv"
    if not val_path.exists() or not idx_path.exists():
        raise SystemExit("missing cache")
    val = pd.read_csv(val_path, parse_dates=["quarter_end", "anchor_date"])
    index_daily = pd.read_csv(idx_path, parse_dates=["date"])
    # 点位：优先用 cache（官方指数 + 早期成分合成点位）；仅补仍为空的季
    if "price" not in val.columns:
        val["price"] = pd.NA
    first_d = pd.Timestamp(index_daily["date"].iloc[0])
    last_d = pd.Timestamp(index_daily["date"].iloc[-1])
    prices = []
    for _, r in val.iterrows():
        if pd.notna(r.get("price")):
            prices.append(float(r["price"]))
            continue
        q = pd.Timestamp(r["quarter_end"])
        if q < first_d:
            prices.append(None)
        elif q > last_d:
            prices.append(float(index_daily.iloc[-1]["close"]))
        else:
            anc = month_end_close(index_daily, q)
            prices.append(anc[1] if anc else None)
    val["price"] = prices
    last = val.iloc[-1]
    pe = float(last["pe"]) if pd.notna(last["pe"]) else None
    pb = float(last["pb"]) if pd.notna(last["pb"]) else None
    price = float(last["price"]) if pd.notna(last["price"]) else float(index_daily.iloc[-1]["close"])
    n = int(last["n"])
    w_cov = float(last["w_cov"])
    return {
        "id": "hstech",
        "title": "恒生科技",
        "code": "HSTECH",
        "asof": pd.Timestamp(index_daily["date"].iloc[-1]).strftime("%Y-%m-%d"),
        "price": price,
        "pe": pe,
        "pb": pb,
        "pe_pct": percentile(val["pe"], pe),
        "pb_pct": percentile(val["pb"], pb),
        "n": n,
        "w_cov": w_cov,
        "val": val,
        "script": "板块：恒生科技 HSTECH。&#10;PE/PB=成分每股盈利年化加权。&#10;只比较位置，数据仅供参考。",
        "note": "有效成分 %d 只 · 权重覆盖约 %.0f%% · 每股盈利年化加权 · 早期点位=成分合成" % (n, w_cov),
    }




def load_hki_sector():
    """港股通互联网：互联网成分每股盈利加权；点位=HSIII（早期成分合成）。"""
    val_path = CACHE / "hki_sector_valuation.csv"
    if not val_path.exists():
        raise SystemExit("missing hki cache")
    val = pd.read_csv(val_path, parse_dates=["quarter_end", "anchor_date"])
    last = val.dropna(subset=["pe"]).iloc[-1]
    pe = float(last["pe"]) if pd.notna(last["pe"]) else None
    pb = float(last["pb"]) if pd.notna(last["pb"]) else None
    price = float(last["price"]) if pd.notna(last["price"]) else None
    n = int(last["n"]) if "n" in last and pd.notna(last["n"]) else int(val["pe"].notna().sum())
    w_cov = float(last["w_cov"]) if "w_cov" in last and pd.notna(last["w_cov"]) else 0.0
    asof = pd.Timestamp(last["anchor_date"]).strftime("%Y-%m-%d")
    return {
        "id": "hki",
        "title": "港股通互联网",
        "code": "HSIII",
        "asof": asof,
        "price": price,
        "pe": pe,
        "pb": pb,
        "pe_pct": percentile(val["pe"], pe),
        "pb_pct": percentile(val["pb"], pb),
        "n": n,
        "w_cov": w_cov,
        "val": val,
        "script": (
            "板块：港股通互联网（恒生互联网成分近似）。&#10;"
            "PE/PB=成分每股盈利年化加权。&#10;"
            "点位近端用HSIII，早期为成分合成。"
        ),
        "note": (
            "点位=HSIII/成分合成 · 每股盈利年化加权 · n=%d · 权重约 %.0f%%"
            % (n, w_cov)
        ),
    }


def load_sse_sector():
    """上证指数：点位=000001；PE/PB=乐咕上证50滚动市盈率/市净率。"""
    val_path = CACHE / "sse_sector_valuation.csv"
    idx_path = CACHE / "sse_index_daily.csv"
    if not val_path.exists() or not idx_path.exists():
        raise SystemExit("missing sse cache; run fetch first")
    val = pd.read_csv(val_path, parse_dates=["quarter_end", "anchor_date"])
    index_daily = pd.read_csv(idx_path, parse_dates=["date"])
    last = val.dropna(subset=["pe"]).iloc[-1]
    pe = float(last["pe"]) if pd.notna(last["pe"]) else None
    pb = float(last["pb"]) if pd.notna(last["pb"]) else None
    price = float(last["price"]) if pd.notna(last["price"]) else float(
        index_daily.iloc[-1]["close"]
    )
    n_pe = int(val["pe"].notna().sum())
    n_pb = int(val["pb"].notna().sum())
    return {
        "id": "sse",
        "title": "上证指数",
        "code": "000001",
        "asof": pd.Timestamp(index_daily["date"].iloc[-1]).strftime("%Y-%m-%d"),
        "price": price,
        "pe": pe,
        "pb": pb,
        "pe_pct": percentile(val["pe"], pe),
        "pb_pct": percentile(val["pb"], pb),
        "n": n_pe,
        "w_cov": 100.0,
        "val": val,
        "script": (
            "板块：上证指数。&#10;"
            "点位用上证综指；PE/PB用上证50滚动（乐咕）。&#10;"
            "不是全市场等权平均。"
        ),
        "note": (
            "点位=上证综指000001 · PE/PB=乐咕上证50滚动 · "
            "有效PE点 %d · PB点 %d" % (n_pe, n_pb)
        ),
    }



def load_cyb_sector():
    """创业板指：点位=399006；PE/PB=乐咕创业板市场平均。"""
    val_path = CACHE / "cyb_sector_valuation.csv"
    idx_path = CACHE / "cyb_index_daily.csv"
    if not val_path.exists() or not idx_path.exists():
        raise SystemExit("missing cyb cache")
    val = pd.read_csv(val_path, parse_dates=["quarter_end", "anchor_date"])
    index_daily = pd.read_csv(idx_path, parse_dates=["date"])
    last = val.dropna(subset=["pe"]).iloc[-1]
    pe = float(last["pe"]) if pd.notna(last["pe"]) else None
    pb = float(last["pb"]) if pd.notna(last["pb"]) else None
    price = float(last["price"]) if pd.notna(last["price"]) else float(
        index_daily.iloc[-1]["close"]
    )
    n_pe = int(val["pe"].notna().sum())
    n_pb = int(val["pb"].notna().sum())
    return {
        "id": "cyb",
        "title": "创业板",
        "code": "399006",
        "asof": pd.Timestamp(index_daily["date"].iloc[-1]).strftime("%Y-%m-%d"),
        "price": price,
        "pe": pe,
        "pb": pb,
        "pe_pct": percentile(val["pe"], pe),
        "pb_pct": percentile(val["pb"], pb),
        "n": n_pe,
        "w_cov": 100.0,
        "val": val,
        "script": (
            "板块：创业板指 399006。&#10;"
            "点位用创业板指；PE/PB为创业板市场平均（乐咕）。&#10;"
            "与恒生科技成分扣非加权口径不同，口播须说明。"
        ),
        "note": (
            "点位=创业板指399006 · PE/PB=乐咕创业板50滚动 · "
            "有效PE点 %d · PB点 %d" % (n_pe, n_pb)
        ),
    }




def load_star_sector():
    """科创板：点位=科创50；PE/PB=乐咕科创版市盈率/市净率。"""
    val_path = CACHE / "star_sector_valuation.csv"
    idx_path = CACHE / "star_index_daily.csv"
    if not val_path.exists() or not idx_path.exists():
        raise SystemExit("missing star cache")
    val = pd.read_csv(val_path, parse_dates=["quarter_end", "anchor_date"])
    index_daily = pd.read_csv(idx_path, parse_dates=["date"])
    last = val.dropna(subset=["pe"]).iloc[-1]
    pe = float(last["pe"]) if pd.notna(last["pe"]) else None
    pb = float(last["pb"]) if pd.notna(last["pb"]) else None
    price = float(last["price"]) if pd.notna(last["price"]) else float(
        index_daily.iloc[-1]["close"]
    )
    n_pe = int(val["pe"].notna().sum())
    n_pb = int(val["pb"].notna().sum())
    return {
        "id": "star",
        "title": "科创板",
        "code": "000688",
        "asof": pd.Timestamp(index_daily["date"].iloc[-1]).strftime("%Y-%m-%d"),
        "price": price,
        "pe": pe,
        "pb": pb,
        "pe_pct": percentile(val["pe"], pe),
        "pb_pct": percentile(val["pb"], pb),
        "n": n_pe,
        "w_cov": 100.0,
        "val": val,
        "script": (
            "板块：科创板（科创50点位）。&#10;"
            "PE/PB用乐咕科创版市盈率/市净率。&#10;"
            "科创估值中枢偏高，口播对照历史分位即可。"
        ),
        "note": (
            "点位=科创50 · PE/PB=乐咕科创版 · 有效PE点 %d · PB点 %d"
            % (n_pe, n_pb)
        ),
    }



def _padded_range(series, pad=0.08):
    s = pd.to_numeric(series, errors="coerce").dropna()
    if s.empty:
        return None
    lo, hi = float(s.min()), float(s.max())
    if lo == hi:
        delta = abs(lo) * 0.1 if lo else 1.0
        return [lo - delta, hi + delta]
    span = hi - lo
    return [lo - span * pad, hi + span * pad]


def val_fig(sector):
    """One chart; PE / PB / 点位 independent y-axes."""
    val = sector["val"]
    x = val["anchor_date"]
    pe = pd.to_numeric(val["pe"], errors="coerce")
    pb = pd.to_numeric(val["pb"], errors="coerce")
    price = pd.to_numeric(val["price"], errors="coerce")
    fig = go.Figure()
    fig.add_trace(
        go.Scatter(
            x=x,
            y=pe,
            mode="lines+markers",
            name="板块PE",
            line=dict(color="#ef5350", width=2),
            marker=dict(size=5),
            connectgaps=False,
            yaxis="y",
            hovertemplate="PE %{y:.1f}<extra></extra>",
        )
    )
    fig.add_trace(
        go.Scatter(
            x=x,
            y=pb,
            mode="lines+markers",
            name="板块PB",
            line=dict(color="#61afef", width=2),
            marker=dict(size=5),
            connectgaps=False,
            yaxis="y2",
            hovertemplate="PB %{y:.2f}<extra></extra>",
        )
    )
    fig.add_trace(
        go.Scatter(
            x=x,
            y=price,
            mode="lines+markers",
            name="点位",
            line=dict(color="#98c379", width=2),
            marker=dict(size=5),
            connectgaps=False,
            yaxis="y3",
            hovertemplate="点位 %{y:.2f}<extra></extra>",
        )
    )
    if sector.get("pe") is not None and pd.notna(sector["pe"]):
        fig.add_hline(
            y=float(sector["pe"]),
            line_dash="dash",
            line_color="#e06c75",
            annotation_text="PE %.1f" % float(sector["pe"]),
        )
    axis = dict(
        showticklabels=False,
        title=None,
        showgrid=True,
        gridcolor="rgba(62,68,81,.35)",
        zeroline=False,
        fixedrange=False,
    )

    def _y(series_range, **kw):
        d = {**axis, **kw}
        if series_range is not None:
            d["range"] = series_range
            d["autorange"] = False
        else:
            d["autorange"] = True
        return d

    fig.update_layout(
        title=None,
        template="plotly_dark",
        height=560,
        margin=dict(l=6, r=6, t=28, b=4),
        legend=dict(
            orientation="h", y=1.02, x=0, font=dict(size=10), bgcolor="rgba(0,0,0,0)"
        ),
        hovermode="x unified",
        dragmode="pan",
        updatemenus=[
            dict(
                type="buttons",
                direction="right",
                x=1,
                y=1.14,
                xanchor="right",
                bgcolor="rgba(40,44,52,.9)",
                font=dict(size=10, color="#abb2bf"),
                buttons=[
                    dict(label="平移", method="relayout", args=[{"dragmode": "pan"}]),
                    dict(label="框选", method="relayout", args=[{"dragmode": "zoom"}]),
                ],
            )
        ],
        xaxis=dict(
            rangeselector=dict(
                bgcolor="rgba(40,44,52,.9)",
                activecolor="#3e4451",
                font=dict(size=10, color="#abb2bf"),
                buttons=[
                    dict(count=1, label="1Y", step="year", stepmode="backward"),
                    dict(count=3, label="3Y", step="year", stepmode="backward"),
                    dict(count=5, label="5Y", step="year", stepmode="backward"),
                    dict(step="all", label="全部"),
                ],
            )
        ),
        yaxis=_y(_padded_range(pe)),
        yaxis2=_y(
            _padded_range(pb),
            overlaying="y",
            side="right",
            showgrid=False,
            anchor="x",
        ),
        yaxis3=_y(
            _padded_range(price),
            overlaying="y",
            side="right",
            showgrid=False,
            anchor="x",
            position=1.0,
        ),
    )
    return fig


def extract_template_shell():
    raw = (ANALYSIS_SRC / "_deck_template.html").read_text(encoding="utf-8")
    js = (ANALYSIS_SRC / "_deck_nav.js").read_text(encoding="utf-8")
    marker = "</" + "body>"
    inject = "<script>" + chr(10) + js + chr(10) + "</script>" + marker
    raw = raw.replace(marker, inject)
    open_tag = "<div class=" + chr(34) + "deck" + chr(34) + " id=" + chr(34) + "deck" + chr(34) + ">"
    start = raw.index(open_tag)
    deck_open_end = start + len(open_tag)
    marker_after = chr(10) + "      </div>" + chr(10) + "    </div>" + chr(10) + "  </div>" + chr(10) + "  <aside class=" + chr(34) + "script-rail" + chr(34)
    deck_close_at = raw.index(marker_after)
    return raw[:deck_open_end], raw[deck_close_at:]


def sector_slide(sector, page, chart_html):
    title = html_lib.escape(sector["title"])
    code = html_lib.escape(sector["code"])
    note = html_lib.escape(sector["note"])
    script = sector["script"]
    q = chr(34)
    parts = []
    parts.append("<section class=" + q + "slide slide-chart" + q + " id=" + q + "slide-" + sector["id"] + q)
    parts.append(" data-page=" + q + str(page) + q + " data-title=" + q + title + q + " data-script=" + q + script + q + ">")
    parts.append("<div class=" + q + "slide-tag" + q + "><span>" + str(page) + " / " + title + "</span><span>" + sector["asof"] + "</span></div>")
    parts.append("<div class=" + q + "slide-inner" + q + ">")
    parts.append("<h2>" + title + " <span style=" + q + "font-weight:500;color:var(--od-muted);font-size:.75em" + q + ">(" + code + ")</span></h2>")
    parts.append("<div class=" + q + "cards" + q + " style=" + q + "flex:0 0 auto;margin-bottom:4px" + q + ">")
    parts.append("<div class=" + q + "card" + q + "><div class=" + q + "label" + q + ">指数点位</div><div class=" + q + "value" + q + ">" + _fmt(sector["price"], 2) + "</div><div class=" + q + "hint" + q + ">最新 / 季末锚点</div></div>")
    parts.append("<div class=" + q + "card" + q + "><div class=" + q + "label" + q + ">板块PE</div><div class=" + q + "value" + q + ">" + _fmt(sector["pe"], 1) + "</div><div class=" + q + "hint" + q + ">历史分位 " + _fmt(sector["pe_pct"], 1, "%") + "</div></div>")
    parts.append("<div class=" + q + "card" + q + "><div class=" + q + "label" + q + ">板块PB</div><div class=" + q + "value" + q + ">" + _fmt(sector["pb"], 2) + "</div><div class=" + q + "hint" + q + ">历史分位 " + _fmt(sector["pb_pct"], 1, "%") + "</div></div>")
    parts.append("<div class=" + q + "card" + q + "><div class=" + q + "label" + q + ">覆盖</div><div class=" + q + "value" + q + ">" + _fmt(sector["w_cov"], 0, "%") + "</div><div class=" + q + "hint" + q + ">n=" + str(sector["n"]) + "</div></div>")
    parts.append("</div>")
    parts.append("<div class=" + q + "panel" + q + "><div class=" + q + "note" + q + ">" + note + "</div><div class=" + q + "chart-box" + q + ">" + chart_html + "</div></div>")
    parts.append("</div></section>")
    return chr(10).join(parts) + chr(10)


def cover_slide(sectors, asof, page):
    names = "、".join(s["title"] for s in sectors)
    q = chr(34)
    cards = []
    for s in sectors:
        cards.append("<div class=" + q + "card" + q + "><div class=" + q + "label" + q + ">" + html_lib.escape(s["title"]) + "</div><div class=" + q + "value" + q + ">" + _fmt(s["pe"], 1) + "</div><div class=" + q + "hint" + q + ">PE · PB " + _fmt(s["pb"], 2) + "</div></div>")
    parts = []
    parts.append("<section class=" + q + "slide" + q + " id=" + q + "slide-cover" + q + " data-page=" + q + str(page) + q + " data-title=" + q + "板块分析" + q + " data-script=" + q + "本期主题：板块分析。&#10;依次过各板块一页：点位、加权PE/PB、分位。&#10;数据仅供参考，不构成决策依据。" + q + ">")
    parts.append("<div class=" + q + "slide-tag" + q + "><span>" + str(page) + " / 封面</span><span>" + asof + "</span></div>")
    parts.append("<div class=" + q + "slide-inner" + q + ">")
    parts.append("<h1 class=" + q + "phone-title" + q + ">板块分析</h1>")
    parts.append("<p class=" + q + "sub" + q + ">本期：" + html_lib.escape(names) + " · 每板块一页 · 上季盈利年化 + 本季末价</p>")
    parts.append("<div class=" + q + "cards" + q + ">" + "".join(cards) + "</div>")
    parts.append("</div></section>")
    return chr(10).join(parts) + chr(10)


def end_slide(page):
    q = chr(34)
    parts = []
    parts.append("<section class=" + q + "slide" + q + " id=" + q + "slide-end" + q + " data-page=" + q + str(page) + q + " data-title=" + q + "收尾说明" + q + " data-script=" + q + "重申：生成数据仅供参考。&#10;邀请观众自己核对官方披露。&#10;结束本页。" + q + ">")
    parts.append("<div class=" + q + "slide-tag" + q + "><span>" + str(page) + " / 结尾</span><span>可口述带过</span></div>")
    parts.append("<div class=" + q + "slide-inner" + q + "><h2>说明</h2>")
    parts.append("<div class=" + q + "disclaimer" + q + ">生成数据仅供参考，不构成任何决策依据。数据来自第三方公开源，请以官方披露为准。板块历史点用当前权重回测，存在偏差。</div>")
    parts.append("<p class=" + q + "sub" + q + ">快捷键：空格/↓ 下一页 · ↑ 上一页 · G 安全区</p>")
    parts.append("</div></section>")
    return chr(10).join(parts) + chr(10)


def render(sectors):
    if not sectors:
        raise SystemExit("no sectors")
    asof = max(s["asof"] for s in sectors)
    charts = {}
    for s in sectors:
        charts[s["id"]] = plot_offline(val_fig(s), output_type="div", include_plotlyjs=False, config={"displayModeBar": False, "responsive": True, "scrollZoom": True, "doubleClick": "reset"})
    total = 1 + len(sectors) + 1
    parts = [cover_slide(sectors, asof, 1)]
    for i, s in enumerate(sectors):
        parts.append(sector_slide(s, i + 2, charts[s["id"]]))
    parts.append(end_slide(total))
    head, tail = extract_template_shell()
    head = head.replace("__NAME__(__CODE__)", "板块分析")
    head = head.replace("__NAME__", "板块分析")
    head = head.replace("__CODE__", "SECTORS")
    tail = tail.replace("__NAME__", "板块分析")
    tail = tail.replace("__CODE__", "SECTORS")
    tail = tail.replace("__ASOF__", asof)
    tail = tail.replace("1/5", "1/%d" % total)
    html = head + chr(10) + "".join(parts) + tail
    OUT.mkdir(parents=True, exist_ok=True)
    path = OUT / "index.html"
    path.write_text(html, encoding="utf-8")
    meta = {
        "niche": "finance",
        "theme": "板块分析",
        "date": EP_DATE,
        "format": "9:16-ppt-deck",
        "layout": "cover + one_page_per_sector + end",
        "sectors": [{
            "id": s["id"], "title": s["title"], "code": s["code"],
            "pe": s["pe"], "pb": s["pb"], "price": s["price"],
            "n": s["n"], "w_cov": s["w_cov"],
        } for s in sectors],
        "pe_method": "mixed_see_sector_notes",
        "sector_pe_notes": {
            "hstech": "hk_basic_eps_ann_weight_avg + index_or_synth_price",
            "hki": "hk_internet_subset_eps_ann_weight_avg + hsiii_or_synth_price",
            "sse": "legulegu_sse50_ttm_pe_pb + sse_index_000001",
            "cyb": "legulegu_cyb50_ttm_pe_pb + cyb_index_399006",
            "star": "legulegu_star_board_pe_pb + star50_000688",
        },
        "generated_at": datetime.now().isoformat(timespec="seconds"),
    }
    (OUT / "meta.json").write_text(json.dumps(meta, ensure_ascii=False, indent=2) + chr(10), encoding="utf-8")
    return path


def main():
    ensure_cache_from_old()
    sectors = [load_hstech_sector(), load_hki_sector(), load_sse_sector(), load_cyb_sector(), load_star_sector()]
    path = render(sectors)
    print("DONE", path)
    print(path.resolve().as_uri())
    if OLD.exists() and (OUT / "index.html").exists():
        shutil.rmtree(OLD)
        print("removed", OLD)


if __name__ == "__main__":
    main()
