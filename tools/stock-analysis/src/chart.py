"""Interactive candlestick chart with Plotly."""

from __future__ import annotations

import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots


def add_ma(df: pd.DataFrame, windows: list[int] | None = None) -> pd.DataFrame:
    out = df.copy()
    windows = windows or [5, 10, 20, 60]
    for w in windows:
        out[f"ma{w}"] = out["close"].rolling(w).mean()
    return out


def build_kline_figure(
    df: pd.DataFrame,
    title: str = "K线图",
    ma_windows: list[int] | None = None,
) -> go.Figure:
    ma_windows = ma_windows or [5, 10, 20, 60]
    data = add_ma(df, ma_windows)

    fig = make_subplots(
        rows=2,
        cols=1,
        shared_xaxes=True,
        vertical_spacing=0.03,
        row_heights=[0.72, 0.28],
    )

    fig.add_trace(
        go.Candlestick(
            x=data["date"],
            open=data["open"],
            high=data["high"],
            low=data["low"],
            close=data["close"],
            name="K线",
            increasing_line_color="#ef5350",
            decreasing_line_color="#26a69a",
        ),
        row=1,
        col=1,
    )

    ma_colors = {5: "#f5c542", 10: "#42a5f5", 20: "#ab47bc", 60: "#ff7043"}
    for w in ma_windows:
        col = f"ma{w}"
        if col in data.columns:
            fig.add_trace(
                go.Scatter(
                    x=data["date"],
                    y=data[col],
                    mode="lines",
                    name=f"MA{w}",
                    line=dict(width=1.2, color=ma_colors.get(w, None)),
                ),
                row=1,
                col=1,
            )

    colors = [
        "#ef5350" if c >= o else "#26a69a"
        for o, c in zip(data["open"], data["close"])
    ]
    fig.add_trace(
        go.Bar(
            x=data["date"],
            y=data["volume"],
            name="成交量",
            marker_color=colors,
            opacity=0.85,
        ),
        row=2,
        col=1,
    )

    fig.update_layout(
        title=title,
        xaxis_rangeslider_visible=False,
        hovermode="x unified",
        template="plotly_white",
        legend=dict(orientation="h", yanchor="bottom", y=1.02, x=0),
        margin=dict(l=40, r=20, t=60, b=40),
        height=720,
        dragmode="pan",
    )
    fig.update_yaxes(title_text="价格", row=1, col=1)
    fig.update_yaxes(title_text="成交量", row=2, col=1)
    fig.update_xaxes(rangeslider_visible=False)
    return fig
