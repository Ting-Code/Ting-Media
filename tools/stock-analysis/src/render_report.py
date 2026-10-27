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

def _kline_figure(daily: pd.DataFrame, title: str) -> go.Figure:
    periods = [('日线', 'D'), ('周线', 'W'), ('月线', 'M'), ('季线', 'Q')]
    fig = make_subplots(rows=2, cols=1, shared_xaxes=True, row_heights=[0.72, 0.28], vertical_spacing=0.03)
    buttons = []
    for i, (label, p) in enumerate(periods):
        df = resample_ohlcv(daily, p)
        visible = [False] * (len(periods) * 2)
        visible[i * 2] = True
        visible[i * 2 + 1] = True
        colors = ['#ef5350' if c >= o else '#26a69a' for o, c in zip(df['open'], df['close'])]
        fig.add_trace(go.Candlestick(x=df['date'], open=df['open'], high=df['high'], low=df['low'], close=df['close'], name='K-' + label, increasing_line_color='#ef5350', decreasing_line_color='#26a69a', visible=(i == 0)), row=1, col=1)
        fig.add_trace(go.Bar(x=df['date'], y=df['volume'], name='V-' + label, marker_color=colors, opacity=0.8, visible=(i == 0), showlegend=False), row=2, col=1)
        buttons.append(dict(label=label, method='update', args=[{'visible': visible}]))
    fig.update_layout(title=None, template='plotly_dark', height=640, margin=dict(l=4, r=4, t=4, b=2), xaxis_rangeslider_visible=False, hovermode='x unified', dragmode='pan', updatemenus=[dict(type='buttons', direction='right', x=0, y=1.08, xanchor='left', buttons=buttons)])
    fig.update_yaxes(title_text='价格', row=1, col=1)
    fig.update_yaxes(title_text='成交量', row=2, col=1)
    return fig


def _fundamental_figure(fundamentals: pd.DataFrame) -> go.Figure:
    df = fundamentals.dropna(subset=['REPORT_DATE']).copy()
    fig = go.Figure()
    fig.add_trace(go.Bar(x=df['REPORT_DATE'], y=df['revenue_q'] / 1e8, name='单季营收(亿)', marker_color='#42a5f5', opacity=0.85))
    fig.add_trace(go.Scatter(x=df['REPORT_DATE'], y=df['deduct_np_q'] / 1e8, name='单季扣非(亿)', mode='lines+markers', yaxis='y2', line=dict(color='#ef6c00', width=2)))
    fig.add_trace(go.Scatter(x=df['REPORT_DATE'], y=df['parent_np_q'] / 1e8, name='单季归母净利(亿)', mode='lines+markers', yaxis='y2', line=dict(color='#7e57c2', width=1.5, dash='dot')))
    fig.update_layout(title=None, template='plotly_dark', height=560, margin=dict(l=6, r=6, t=6, b=4), yaxis=dict(title='营收(亿元)'), yaxis2=dict(title='利润(亿元)', overlaying='y', side='right'), legend=dict(orientation='h', y=1.0, x=0, font=dict(size=10), bgcolor='rgba(0,0,0,0)'), hovermode='x unified')
    return fig


def _valuation_figure(val: pd.DataFrame, snap: dict) -> go.Figure:
    fig = make_subplots(specs=[[{'secondary_y': True}]])
    fig.add_trace(go.Scatter(x=val['anchor_date'], y=val['pe_ttm_deduct'], mode='lines+markers', name='动态PE(TTM扣非)', line=dict(color='#ef5350', width=2)), secondary_y=False)
    fig.add_trace(go.Scatter(x=val['anchor_date'], y=val['pb'], mode='lines+markers', name='PB', line=dict(color='#42a5f5', width=1.5)), secondary_y=True)
    fig.add_trace(go.Scatter(x=val['anchor_date'], y=val['div_yield_pct'], mode='lines+markers', name='股息率%', line=dict(color='#26a69a', width=1.5, dash='dot')), secondary_y=True)
    if snap.get('pe_ttm_deduct') is not None:
        fig.add_hline(y=snap['pe_ttm_deduct'], line_dash='dash', line_color='#c62828', annotation_text='当前PE %.1f' % snap['pe_ttm_deduct'], secondary_y=False)
    fig.update_layout(title=None, template='plotly_dark', height=560, margin=dict(l=6, r=6, t=6, b=4), legend=dict(orientation='h', y=1.0, x=0, font=dict(size=10), bgcolor='rgba(0,0,0,0)'), hovermode='x unified')
    fig.update_yaxes(title_text='PE', secondary_y=False)
    fig.update_yaxes(title_text='PB / 股息率%', secondary_y=True)
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
    pe_pct = percentile(valuation["pe_ttm_deduct"], snap.get("pe_ttm_deduct"))
    pb_pct = percentile(valuation["pb"], snap.get("pb"))
    div_pct = percentile(valuation["div_yield_pct"], snap.get("div_yield_pct"))
    k_html = plot_offline(_kline_figure(daily, "%s(%s)" % (name, code)), output_type="div", include_plotlyjs=False, config={"displayModeBar": False, "responsive": True})
    f_html = plot_offline(_fundamental_figure(fundamentals), output_type="div", include_plotlyjs=False, config={"displayModeBar": False, "responsive": True})
    v_html = plot_offline(_valuation_figure(valuation, snap), output_type="div", include_plotlyjs=False, config={"displayModeBar": False, "responsive": True})
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
