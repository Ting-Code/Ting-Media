"""Render 9:16 PPT-style review HTML with safe areas."""
from __future__ import annotations
from pathlib import Path
import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots
from plotly.offline import plot as plot_offline
from _pathsetup import ensure_stock_data_on_path

ensure_stock_data_on_path()
from market import resample_ohlcv  # noqa: E402
from valuation import percentile  # noqa: E402

PLOT_CONFIG = {
    "displayModeBar": False,
    "responsive": True,
    "scrollZoom": True,
    "doubleClick": "reset",
}


def _axis_hide(**extra):
    d = dict(
        showticklabels=False,
        title=None,
        showgrid=True,
        gridcolor="rgba(62,68,81,.35)",
        zeroline=False,
        fixedrange=False,
    )
    d.update(extra)
    return d


def _range_selectors():
    return dict(
        bgcolor="rgba(40,44,52,.9)",
        activecolor="#3e4451",
        font=dict(size=10, color="#abb2bf"),
        x=0,
        y=1.12,
        buttons=[
            dict(count=1, label="1Y", step="year", stepmode="backward"),
            dict(count=3, label="3Y", step="year", stepmode="backward"),
            dict(count=5, label="5Y", step="year", stepmode="backward"),
            dict(step="all", label="全部"),
        ],
    )


def _mode_buttons(y=1.12, x=1):
    """Pan / box-zoom toggle (right side)."""
    return dict(
        type="buttons",
        direction="right",
        x=x,
        y=y,
        xanchor="right",
        pad=dict(r=0, t=0),
        bgcolor="rgba(40,44,52,.9)",
        font=dict(size=10, color="#abb2bf"),
        buttons=[
            dict(label="平移", method="relayout", args=[{"dragmode": "pan"}]),
            dict(label="框选", method="relayout", args=[{"dragmode": "zoom"}]),
        ],
    )


def _kline_figure(daily: pd.DataFrame, title: str) -> go.Figure:
    periods = [("日线", "D"), ("周线", "W"), ("月线", "M"), ("季线", "Q")]
    fig = make_subplots(
        rows=2,
        cols=1,
        shared_xaxes=True,
        row_heights=[0.72, 0.28],
        vertical_spacing=0.03,
    )
    buttons = []
    for i, (label, p) in enumerate(periods):
        df = resample_ohlcv(daily, p)
        visible = [False] * (len(periods) * 2)
        visible[i * 2] = True
        visible[i * 2 + 1] = True
        colors = [
            "#ef5350" if c >= o else "#26a69a"
            for o, c in zip(df["open"], df["close"])
        ]
        fig.add_trace(
            go.Candlestick(
                x=df["date"],
                open=df["open"],
                high=df["high"],
                low=df["low"],
                close=df["close"],
                name="K-" + label,
                increasing_line_color="#ef5350",
                decreasing_line_color="#26a69a",
                visible=(i == 0),
            ),
            row=1,
            col=1,
        )
        fig.add_trace(
            go.Bar(
                x=df["date"],
                y=df["volume"],
                name="V-" + label,
                marker_color=colors,
                opacity=0.8,
                visible=(i == 0),
                showlegend=False,
            ),
            row=2,
            col=1,
        )
        buttons.append(
            dict(label=label, method="update", args=[{"visible": visible}])
        )
    fig.update_layout(
        title=None,
        template="plotly_dark",
        height=640,
        margin=dict(l=4, r=4, t=28, b=2),
        xaxis_rangeslider_visible=False,
        hovermode="x unified",
        dragmode="pan",
        updatemenus=[
            dict(
                type="buttons",
                direction="right",
                x=0,
                y=1.14,
                xanchor="left",
                buttons=buttons,
                bgcolor="rgba(40,44,52,.9)",
                font=dict(size=10, color="#abb2bf"),
            ),
            _mode_buttons(y=1.14, x=1),
        ],
    )
    fig.update_xaxes(rangeselector=_range_selectors(), row=1, col=1)
    fig.update_xaxes(matches="x", row=2, col=1)
    fig.update_yaxes(**_axis_hide(), row=1, col=1)
    fig.update_yaxes(**_axis_hide(showgrid=False), row=2, col=1)
    return fig


def _fundamental_figure(fundamentals: pd.DataFrame) -> go.Figure:
    df = fundamentals.dropna(subset=["REPORT_DATE"]).copy()
    fig = go.Figure()
    fig.add_trace(
        go.Bar(
            x=df["REPORT_DATE"],
            y=df["revenue_q"] / 1e8,
            name="单季营收(亿)",
            marker_color="#42a5f5",
            opacity=0.85,
        )
    )
    fig.add_trace(
        go.Scatter(
            x=df["REPORT_DATE"],
            y=df["deduct_np_q"] / 1e8,
            name="单季扣非(亿)",
            mode="lines+markers",
            yaxis="y2",
            line=dict(color="#ef6c00", width=2),
        )
    )
    if "parent_np_q" in df.columns:
        fig.add_trace(
            go.Scatter(
                x=df["REPORT_DATE"],
                y=df["parent_np_q"] / 1e8,
                name="单季归母净利(亿)",
                mode="lines+markers",
                yaxis="y2",
                line=dict(color="#7e57c2", width=1.5, dash="dot"),
            )
        )
    fig.update_layout(
        title=None,
        template="plotly_dark",
        height=560,
        margin=dict(l=6, r=6, t=28, b=4),
        yaxis=_axis_hide(),
        yaxis2=_axis_hide(overlaying="y", side="right", showgrid=False),
        dragmode="pan",
        legend=dict(
            orientation="h",
            y=1.0,
            x=0,
            font=dict(size=10),
            bgcolor="rgba(0,0,0,0)",
        ),
        hovermode="x unified",
        updatemenus=[_mode_buttons(y=1.14)],
        xaxis=dict(rangeselector=_range_selectors()),
    )
    return fig


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


def _y_axis(series_range, **kw):
    base = _axis_hide(**kw)
    if series_range is not None:
        base["range"] = series_range
        base["autorange"] = False
    else:
        base["autorange"] = True
    return base


def _valuation_figure(val: pd.DataFrame, snap: dict) -> go.Figure:
    """One chart; PE / PB / price each on its own y-axis (no shared scale, no rebase)."""
    x = val["anchor_date"] if "anchor_date" in val.columns else val["quarter_end"]
    pe_col = "pe" if "pe" in val.columns else "pe_ttm_deduct"
    pe = pd.to_numeric(val[pe_col], errors="coerce")
    pb = pd.to_numeric(val["pb"], errors="coerce")
    price = pd.to_numeric(val["price"], errors="coerce")

    fig = go.Figure()
    fig.add_trace(
        go.Scatter(
            x=x,
            y=pe,
            mode="lines+markers",
            name="PE",
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
            name="PB",
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
            name="股价",
            line=dict(color="#98c379", width=2),
            marker=dict(size=5),
            connectgaps=False,
            yaxis="y3",
            hovertemplate="股价 %{y:.2f}<extra></extra>",
        )
    )
    pe_now = snap.get("pe", snap.get("pe_ttm_deduct"))
    if pe_now is not None and pd.notna(pe_now):
        fig.add_hline(
            y=float(pe_now),
            line_dash="dash",
            line_color="#e06c75",
            annotation_text="PE %.1f" % float(pe_now),
        )

    fig.update_layout(
        title=None,
        template="plotly_dark",
        height=560,
        margin=dict(l=6, r=6, t=28, b=4),
        legend=dict(
            orientation="h",
            y=1.02,
            x=0,
            font=dict(size=10),
            bgcolor="rgba(0,0,0,0)",
        ),
        hovermode="x unified",
        dragmode="pan",
        updatemenus=[_mode_buttons(y=1.14)],
        xaxis=dict(rangeselector=_range_selectors()),
        yaxis=_y_axis(_padded_range(pe)),
        yaxis2=_y_axis(
            _padded_range(pb),
            overlaying="y",
            side="right",
            showgrid=False,
            anchor="x",
        ),
        yaxis3=_y_axis(
            _padded_range(price),
            overlaying="y",
            side="right",
            showgrid=False,
            anchor="x",
            position=1.0,
        ),
    )
    return fig


def _fmt(v, nd=2, suffix=''):
    if v is None or (isinstance(v, float) and pd.isna(v)):
        return '-'
    return (('%.' + str(nd) + 'f') % v) + suffix



def _load_deck_template() -> str:
    base = Path(__file__).resolve().parent
    html = (base / "_deck_template.html").read_text(encoding="utf-8")
    js = (base / "_deck_nav.js").read_text(encoding="utf-8")
    marker = "</" + "body>"
    if marker not in html:
        raise RuntimeError("deck template missing body end tag")
    inject = "<script>" + chr(10) + js + chr(10) + "</script>" + marker
    return html.replace(marker, inject)


def render_html(*, name, code, daily, fundamentals, valuation, snap, out_path):
    pe_col = "pe" if "pe" in valuation.columns else "pe_ttm_deduct"
    pe_pct = percentile(valuation[pe_col], snap.get("pe", snap.get("pe_ttm_deduct")))
    pb_pct = percentile(valuation["pb"], snap.get("pb"))
    div_pct = percentile(valuation["div_yield_pct"], snap.get("div_yield_pct"))
    k_html = plot_offline(_kline_figure(daily, "%s(%s)" % (name, code)), output_type="div", include_plotlyjs=False, config=PLOT_CONFIG)
    f_html = plot_offline(_fundamental_figure(fundamentals), output_type="div", include_plotlyjs=False, config=PLOT_CONFIG)
    v_html = plot_offline(_valuation_figure(valuation, snap), output_type="div", include_plotlyjs=False, config=PLOT_CONFIG)
    asof = pd.Timestamp(snap["asof"]).strftime("%Y-%m-%d")
    html = _load_deck_template()
    reps = {
        "__NAME__": name,
        "__CODE__": code,
        "__ASOF__": asof,
        "__PRICE__": _fmt(snap["price"]),
        "__PE__": _fmt(snap.get("pe_ttm_deduct"), 1),
        "__PE_PCT__": _fmt(pe_pct, 1, "%"),
        "__PB__": _fmt(snap.get("pb"), 2),
        "__PB_PCT__": _fmt(pb_pct, 1, "%"),
        "__DIV__": _fmt(snap.get("div_yield_pct"), 2, "%"),
        "__DIV_PCT__": _fmt(div_pct, 1, "%"),
        "__K__": k_html,
        "__F__": f_html,
        "__V__": v_html,
    }
    for key, val in reps.items():
        html = html.replace(key, val)
    out_path = Path(out_path)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(html, encoding="utf-8")
    return out_path
