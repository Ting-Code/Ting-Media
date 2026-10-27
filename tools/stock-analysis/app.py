"""Legacy Streamlit entry (optional). Prefer scripts/generate_stock_html.py.

Requires: pip install -r requirements.txt and ../stock-data/requirements.txt
"""

from __future__ import annotations

from datetime import date, timedelta
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT / "src"))
from _pathsetup import ensure_stock_data_on_path

ensure_stock_data_on_path()

import streamlit as st
from codes import resolve_code
from market import fetch_daily
from chart import build_kline_figure

st.set_page_config(page_title="交互K线（试验）", layout="wide")
st.title("交互 K 线图（试验）")
st.caption("正式录屏请用 scripts/generate_stock_html.py")

with st.sidebar:
    q = st.text_input("代码或名称", value="600519")
    today = date.today()
    start = st.date_input("开始", value=today - timedelta(days=365 * 3))
    end = st.date_input("结束", value=today)
    load = st.button("加载", type="primary")

if load:
    code, name = resolve_code(q)
    df = fetch_daily(code, start_date=start.strftime("%Y-%m-%d"), end_date=end.strftime("%Y-%m-%d"))
    st.plotly_chart(build_kline_figure(df, title=f"{name}({code})"), use_container_width=True)
else:
    st.write("侧边栏输入后加载。")
