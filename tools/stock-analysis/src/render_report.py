"""Render single-stock review HTML with Plotly charts (portrait 9:16 first)."""
from __future__ import annotations
from pathlib import Path
import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots
from plotly.offline import plot as plot_offline
from .market import resample_ohlcv
from .valuation import percentile

TEMPLATE = """<!DOCTYPE html>
<html lang="zh-CN"><head>
<meta charset="utf-8"/>
<meta name="viewport" content="width=device-width, initial-scale=1, viewport-fit=cover"/>
<meta name="color-scheme" content="light"/>
<title>__NAME__(__CODE__) 复盘页</title>
<script src="https://cdn.plot.ly/plotly-2.35.2.min.js"></script>
<style>
:root{
  --bg:#f3efe6; --ink:#1c1917; --muted:#78716c; --card:#fffdf8;
  --line:#e5ddd0; --accent:#0f766e; --stage:420px;
}
*{box-sizing:border-box}
html,body{margin:0;padding:0}
body{
  font-family:"Segoe UI","PingFang SC","Microsoft YaHei",sans-serif;
  background:
    radial-gradient(1200px 600px at 50% -10%, #e8dfd0 0%, transparent 60%),
    var(--bg);
  color:var(--ink); line-height:1.55;
  min-height:100dvh;
}
/* 竖屏主舞台：约手机 9:16 宽度，纵向长页便于短视频分镜截取 */
.stage{
  width:min(100vw, var(--stage));
  margin:0 auto;
  min-height:100dvh;
  padding: max(16px, env(safe-area-inset-top)) 14px 48px;
}
.phone-hint{
  display:flex; justify-content:space-between; align-items:center;
  color:var(--muted); font-size:.72rem; letter-spacing:.04em;
  margin-bottom:10px; text-transform:none;
}
.phone-hint span{opacity:.85}
h1{font-size:1.55rem; margin:0 0 6px; letter-spacing:.01em; line-height:1.25}
.sub{color:var(--muted); font-size:.84rem; margin-bottom:14px}
.cards{
  display:grid; grid-template-columns:1fr 1fr; gap:10px;
  margin:0 0 16px;
}
.card{
  background:var(--card); border:1px solid var(--line);
  border-radius:14px; padding:12px 12px 10px;
}
.card .label{color:var(--muted); font-size:.75rem}
.card .value{font-size:1.22rem; font-weight:650; margin-top:4px; word-break:break-all}
.card .hint{color:var(--muted); font-size:.7rem; margin-top:4px; line-height:1.35}
section{
  background:var(--card); border:1px solid var(--line);
  border-radius:16px; padding:12px 8px 6px; margin-bottom:14px;
  /* 单块接近竖屏分镜高度，方便截短视频画面 */
  scroll-margin-top:12px;
}
h2{font-size:.98rem; margin:2px 8px 6px; color:var(--accent)}
.note{color:var(--muted); font-size:.78rem; padding:0 8px 6px; line-height:1.4}
.disclaimer{
  margin-top:18px; padding:12px 14px;
  border-left:3px solid var(--accent);
  background:#fff; color:var(--muted); font-size:.78rem;
}
/* 宽屏也保持竖屏栏，两侧留白，避免被拉成横版仪表盘 */
@media (min-width: 900px){
  body{background-color:#ebe4d8}
  .stage{
    box-shadow:0 18px 50px rgba(28,25,23,.08);
    background:linear-gradient(180deg,#f7f2e9 0%, var(--bg) 180px);
    border-left:1px solid var(--line); border-right:1px solid var(--line);
  }
}
.js-plotly-plot, .plotly{max-width:100% !important}
</style></head><body>
<div class="stage">
  <div class="phone-hint"><span>竖屏 9:16 · 短视频友好</span><span>__ASOF__</span></div>
  <h1>__NAME__ <span style="font-weight:500;color:var(--muted);font-size:.72em">(__CODE__)</span></h1>
  <div class="sub">单票复盘 · 前复权 · 估值锚定：季报发布日次月月末收盘</div>
  <div class="cards">
    <div class="card"><div class="label">现价</div><div class="value">__PRICE__</div><div class="hint">最新交易日收盘</div></div>
    <div class="card"><div class="label">动态PE · TTM扣非</div><div class="value">__PE__</div><div class="hint">历史分位 __PE_PCT__</div></div>
    <div class="card"><div class="label">市净率 PB</div><div class="value">__PB__</div><div class="hint">历史分位 __PB_PCT__</div></div>
    <div class="card"><div class="label">股息率</div><div class="value">__DIV__</div><div class="hint">近12月现金分红/现价 · 分位 __DIV_PCT__</div></div>
  </div>
  <section id="kline"><h2>A. 行情 K 线</h2><div class="note">切换日/周/月/季 · 缩放拖动</div>__K__</section>
  <section id="fund"><h2>B. 季度营收与利润</h2><div class="note">累计报表已拆单季 · 扣非=归母扣非净利</div>__F__</section>
  <section id="val"><h2>C. 估值序列 vs 现价</h2><div class="note">锚定=NOTICE次月月末收盘 / TTM扣非每股 · 红虚线=当前PE</div>__V__</section>
  <div class="disclaimer">仅供学习与复盘展示，不构成投资建议。数据来自 BaoStock / 东财(AkShare)，请以官方披露为准。</div>
</div>
</body></html>
"""


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
    fig.update_layout(title=title, template='plotly_white', height=520, margin=dict(l=28, r=12, t=70, b=24), xaxis_rangeslider_visible=False, hovermode='x unified', dragmode='pan', updatemenus=[dict(type='buttons', direction='right', x=0, y=1.16, xanchor='left', buttons=buttons)])
    fig.update_yaxes(title_text='价格', row=1, col=1)
    fig.update_yaxes(title_text='成交量', row=2, col=1)
    return fig


def _fundamental_figure(fundamentals: pd.DataFrame) -> go.Figure:
    df = fundamentals.dropna(subset=['REPORT_DATE']).copy()
    fig = go.Figure()
    fig.add_trace(go.Bar(x=df['REPORT_DATE'], y=df['revenue_q'] / 1e8, name='单季营收(亿)', marker_color='#42a5f5', opacity=0.85))
    fig.add_trace(go.Scatter(x=df['REPORT_DATE'], y=df['deduct_np_q'] / 1e8, name='单季扣非(亿)', mode='lines+markers', yaxis='y2', line=dict(color='#ef6c00', width=2)))
    fig.add_trace(go.Scatter(x=df['REPORT_DATE'], y=df['parent_np_q'] / 1e8, name='单季归母净利(亿)', mode='lines+markers', yaxis='y2', line=dict(color='#7e57c2', width=1.5, dash='dot')))
    fig.update_layout(title='上市以来季度盈利（累计报表已拆单季）', template='plotly_white', height=380, margin=dict(l=28, r=36, t=56, b=24), yaxis=dict(title='营收(亿元)'), yaxis2=dict(title='利润(亿元)', overlaying='y', side='right'), legend=dict(orientation='h', y=1.08), hovermode='x unified')
    return fig


def _valuation_figure(val: pd.DataFrame, snap: dict) -> go.Figure:
    fig = make_subplots(specs=[[{'secondary_y': True}]])
    fig.add_trace(go.Scatter(x=val['anchor_date'], y=val['pe_ttm_deduct'], mode='lines+markers', name='动态PE(TTM扣非)', line=dict(color='#ef5350', width=2)), secondary_y=False)
    fig.add_trace(go.Scatter(x=val['anchor_date'], y=val['pb'], mode='lines+markers', name='PB', line=dict(color='#42a5f5', width=1.5)), secondary_y=True)
    fig.add_trace(go.Scatter(x=val['anchor_date'], y=val['div_yield_pct'], mode='lines+markers', name='股息率%', line=dict(color='#26a69a', width=1.5, dash='dot')), secondary_y=True)
    if snap.get('pe_ttm_deduct') is not None:
        fig.add_hline(y=snap['pe_ttm_deduct'], line_dash='dash', line_color='#c62828', annotation_text='当前PE %.1f' % snap['pe_ttm_deduct'], secondary_y=False)
    fig.update_layout(title='估值序列：季报发布日后次月月末收盘锚定', template='plotly_white', height=380, margin=dict(l=28, r=36, t=56, b=24), legend=dict(orientation='h', y=1.08), hovermode='x unified')
    fig.update_yaxes(title_text='PE', secondary_y=False)
    fig.update_yaxes(title_text='PB / 股息率%', secondary_y=True)
    return fig


def _fmt(v, nd=2, suffix=''):
    if v is None or (isinstance(v, float) and pd.isna(v)):
        return '-'
    return (('%.' + str(nd) + 'f') % v) + suffix


def render_html(*, name, code, daily, fundamentals, valuation, snap, out_path):
    pe_pct = percentile(valuation['pe_ttm_deduct'], snap.get('pe_ttm_deduct'))
    pb_pct = percentile(valuation['pb'], snap.get('pb'))
    div_pct = percentile(valuation['div_yield_pct'], snap.get('div_yield_pct'))
    k_html = plot_offline(_kline_figure(daily, '%s(%s) 行情K线' % (name, code)), output_type='div', include_plotlyjs=False)
    f_html = plot_offline(_fundamental_figure(fundamentals), output_type='div', include_plotlyjs=False)
    v_html = plot_offline(_valuation_figure(valuation, snap), output_type='div', include_plotlyjs=False)
    asof = pd.Timestamp(snap['asof']).strftime('%Y-%m-%d')
    html = TEMPLATE
    reps = {
        '__NAME__': name, '__CODE__': code, '__ASOF__': asof,
        '__PRICE__': _fmt(snap['price']),
        '__PE__': _fmt(snap.get('pe_ttm_deduct'), 1),
        '__PE_PCT__': _fmt(pe_pct, 1, '%'),
        '__PB__': _fmt(snap.get('pb'), 2),
        '__PB_PCT__': _fmt(pb_pct, 1, '%'),
        '__DIV__': _fmt(snap.get('div_yield_pct'), 2, '%'),
        '__DIV_PCT__': _fmt(div_pct, 1, '%'),
        '__K__': k_html, '__F__': f_html, '__V__': v_html,
    }
    for k, v in reps.items():
        html = html.replace(k, v)
    out_path = Path(out_path)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(html, encoding='utf-8')
    return out_path

