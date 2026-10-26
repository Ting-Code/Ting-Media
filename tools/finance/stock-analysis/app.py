"""Interactive A-share K-line viewer.

Run:
    streamlit run app.py
"""

from __future__ import annotations

from datetime import date, timedelta

import streamlit as st

from src.chart import build_kline_figure
from src.data_loader import fetch_daily

st.set_page_config(page_title="A股交互K线", layout="wide")
st.title("A股交互 K 线图")
st.caption("数据源：BaoStock（前复权日线）· 图表：Plotly（可缩放/拖动/悬停）")

with st.sidebar:
    st.header("参数")
    code = st.text_input("股票代码", value="600519", help="支持 600519 / sh.600519 / 600519.SH")
    today = date.today()
    start = st.date_input("开始日期", value=today - timedelta(days=365 * 3))
    end = st.date_input("结束日期", value=today)
    ma_options = st.multiselect("均线", options=[5, 10, 20, 60, 120], default=[5, 10, 20, 60])
    load = st.button("加载K线", type="primary")

if load:
    try:
        with st.spinner("正在拉取日线数据..."):
            df = fetch_daily(
                code,
                start_date=start.strftime("%Y-%m-%d"),
                end_date=end.strftime("%Y-%m-%d"),
            )
        symbol = df["code"].iloc[0]
        fig = build_kline_figure(
            df,
            title=f"{symbol} 日线 K 线",
            ma_windows=ma_options or [5, 10, 20, 60],
        )
        st.plotly_chart(fig, use_container_width=True)
        with st.expander("原始数据"):
            st.dataframe(df, use_container_width=True)
        st.info("操作提示：滚轮缩放 · 按住拖动平移 · 双击重置 · 工具栏可框选放大")
    except Exception as exc:
        st.error(str(exc))
else:
    st.write("在左侧输入股票代码后点击「加载K线」。")
