# -*- coding: utf-8 -*-
"""One-off: Hang Seng TECH sector episode under new PE/PB rules.

口径: 上一报告期股东应占溢利(年化) + 本季末价(未结束用最新价);
板块 PE/PB = 权重加权。港股无 A 股「扣非」时用股东应占溢利近似。
"""
from __future__ import annotations

import json
import sys
import time
from datetime import date, datetime
from pathlib import Path

import akshare as ak
import pandas as pd
import plotly.graph_objects as go
from plotly.offline import plot as plot_offline
from plotly.subplots import make_subplots

ROOT = Path(r"D:/project/ting/Ting-Media")
OUT = ROOT / "episodes/finance" / f"{date.today().isoformat()}_恒生科技板块PE"
CACHE = OUT / "cache"

# Weights from HSI Aug-2026 review (approx 变動後); codes zero-padded 5 digits
# Source: HSI press release attachment (disclosed in episode meta)
WEIGHTS = {
    "00700": 8.00,  # 腾讯
    "01810": 8.00,  # 小米
    "09988": 8.00,  # 阿里
    "03690": 8.00,  # 美团
    "01211": 8.00,  # 比亚迪
    "09999": 7.50,  # 网易 (approx)
    "00981": 6.30,  # 中芯
    "09618": 5.06,  # 京东
    "01024": 3.32,  # 快手
    "09888": 4.08,  # 百度
    "09961": 3.55,  # 携程
    "09868": 2.17,  # 小鹏
    "02015": 1.89,  # 理想
    "00300": 1.74,  # 美的
    "06690": 1.49,  # 海尔
    "09626": 1.24,  # B站
    "00992": 2.20,  # 联想
    "01347": 0.94,  # 华虹
    "00285": 0.81,  # 比亚迪电子
    "02382": 1.59,  # 舜宇
    "06618": 1.94,  # 京东健康
    "00241": 0.94,  # 阿里健康
    "09866": 0.60,  # 蔚来
    "00020": 1.32,  # 商汤
    "09660": 2.07,  # 地平线
}


def pad(code: str) -> str:
    return str(code).zfill(5)


def fetch_index_daily() -> pd.DataFrame:
    df = ak.stock_hk_index_daily_sina(symbol="HSTECH")
    df["date"] = pd.to_datetime(df["date"])
    for c in ["open", "high", "low", "close", "volume"]:
        if c in df.columns:
            df[c] = pd.to_numeric(df[c], errors="coerce")
    return df.dropna(subset=["close"]).sort_values("date").reset_index(drop=True)


def fetch_stock_daily(code: str) -> pd.DataFrame:
    df = ak.stock_hk_daily(symbol=code, adjust="qfq")
    df["date"] = pd.to_datetime(df["date"])
    for c in ["open", "high", "low", "close", "volume"]:
        if c in df.columns:
            df[c] = pd.to_numeric(df[c], errors="coerce")
    return df.dropna(subset=["close"]).sort_values("date").reset_index(drop=True)


def retry(fn, tries=4, sleep_s=1.2):
    last = None
    for i in range(tries):
        try:
            return fn()
        except Exception as e:
            last = e
            time.sleep(sleep_s * (i + 1))
    raise last


def fetch_earnings_equity(code: str) -> pd.DataFrame:
    """Report-period 股东应占溢利 + 股东权益; amounts may be YTD — keep as period total and annualize by months."""
    profit = ak.stock_financial_hk_report_em(
        stock=code, symbol="利润表", indicator="报告期"
    )
    bal = ak.stock_financial_hk_report_em(
        stock=code, symbol="资产负债表", indicator="报告期"
    )
    pe = profit[profit["STD_ITEM_NAME"] == "股东应占溢利"][
        ["REPORT_DATE", "START_DATE", "AMOUNT"]
    ].copy()
    pe = pe.rename(columns={"AMOUNT": "earnings"})
    eq = bal[bal["STD_ITEM_NAME"] == "股东权益"][["REPORT_DATE", "AMOUNT"]].copy()
    eq = eq.rename(columns={"AMOUNT": "equity"})
    if pe.empty or eq.empty:
        return pd.DataFrame()
    pe["REPORT_DATE"] = pd.to_datetime(pe["REPORT_DATE"])
    pe["START_DATE"] = pd.to_datetime(pe["START_DATE"])
    eq["REPORT_DATE"] = pd.to_datetime(eq["REPORT_DATE"])
    m = pe.merge(eq, on="REPORT_DATE", how="inner")
    m["months"] = (
        (m["REPORT_DATE"].dt.to_period("M") - m["START_DATE"].dt.to_period("M")).apply(
            lambda x: x.n + 1 if pd.notna(x) else 12
        )
    )
    m["months"] = m["months"].clip(lower=1, upper=12)
    m["earnings_ann"] = m["earnings"] * (12.0 / m["months"])
    return m.sort_values("REPORT_DATE").drop_duplicates("REPORT_DATE", keep="last")


def month_end_close(daily: pd.DataFrame, day: pd.Timestamp):
    sub = daily[daily["date"] <= day]
    if sub.empty:
        return None
    row = sub.iloc[-1]
    return pd.Timestamp(row["date"]), float(row["close"])


def stock_points(code: str, daily: pd.DataFrame, fin: pd.DataFrame) -> pd.DataFrame:
    if fin.empty or daily.empty:
        return pd.DataFrame()
    last_daily = pd.Timestamp(daily["date"].iloc[-1]).normalize()
    first = fin["REPORT_DATE"].min()
    start_obs = (first.to_period("Q") + 1).to_timestamp(how="end")
    end_obs = last_daily.to_period("Q").to_timestamp(how="end")
    if start_obs > end_obs:
        return pd.DataFrame()
    q_ends = pd.period_range(
        start_obs.to_period("Q"), end_obs.to_period("Q"), freq="Q"
    ).to_timestamp(how="end")
    rows = []
    fin = fin.sort_values("REPORT_DATE")
    for q_end in q_ends:
        q_end = pd.Timestamp(q_end).normalize()
        prev_period = (q_end.to_period("Q") - 1).to_timestamp(how="end")
        # latest report with REPORT_DATE <= prev quarter end
        sub = fin[fin["REPORT_DATE"] <= prev_period]
        if sub.empty:
            continue
        r = sub.iloc[-1]
        incomplete = q_end > last_daily
        if incomplete:
            price_date, price = last_daily, float(daily.iloc[-1]["close"])
        else:
            anc = month_end_close(daily, q_end)
            if anc is None:
                continue
            price_date, price = anc
        earn = float(r["earnings_ann"])
        equity = float(r["equity"])
        if equity <= 0 or price <= 0:
            continue
        # PE = price / (earnings_ann / shares) — without shares use equity-based book and
        # PE via earnings yield on market: need shares. Approx PE = mcap/earnings.
        # Without shares: use PB = price/(equity/shares) needs shares.
        # From 每股: if we only have total earnings & equity, PE = (price * shares)/earn
        # Use PB = mcap/equity if we get shares from 股本 item — fetch once
        pe = None
        pb = None
        rows.append(
            {
                "code": code,
                "quarter_end": q_end,
                "anchor_date": price_date,
                "price": price,
                "earnings_ann": earn,
                "equity": equity,
                "prev_report": r["REPORT_DATE"],
                "incomplete": incomplete,
            }
        )
    return pd.DataFrame(rows)


def attach_shares_and_multiples(code: str, points: pd.DataFrame) -> pd.DataFrame:
    if points.empty:
        return points
    try:
        bal = ak.stock_financial_hk_report_em(
            stock=code, symbol="资产负债表", indicator="报告期"
        )
        sh = bal[bal["STD_ITEM_NAME"] == "股本"][["REPORT_DATE", "AMOUNT"]].copy()
        sh["REPORT_DATE"] = pd.to_datetime(sh["REPORT_DATE"])
        sh = sh.rename(columns={"AMOUNT": "share_capital"}).sort_values("REPORT_DATE")
    except Exception:
        return points
    out = []
    for _, row in points.iterrows():
        sub = sh[sh["REPORT_DATE"] <= row["prev_report"]]
        if sub.empty or float(sub.iloc[-1]["share_capital"]) <= 0:
            continue
        shares = float(sub.iloc[-1]["share_capital"])
        # HK 股本 sometimes in thousands of shares or HKD share capital — EM usually 股数
        pe = (
            row["price"] / (row["earnings_ann"] / shares)
            if row["earnings_ann"] > 0
            else None
        )
        pb = row["price"] / (row["equity"] / shares) if row["equity"] > 0 else None
        d = row.to_dict()
        d["shares"] = shares
        d["pe"] = pe
        d["pb"] = pb
        out.append(d)
    return pd.DataFrame(out)


def aggregate(points: pd.DataFrame, weights: dict) -> pd.DataFrame:
    """Weight-average PE/PB; index-like price from HSTECH daily filled later."""
    if points.empty:
        return pd.DataFrame()
    points = points.copy()
    points["w"] = points["code"].map(lambda c: weights.get(c, 0.0))
    rows = []
    for q, g in points.groupby("quarter_end"):
        g = g.dropna(subset=["pe", "pb"])
        g = g[g["w"] > 0]
        if g.empty:
            continue
        wsum = g["w"].sum()
        rows.append(
            {
                "quarter_end": q,
                "anchor_date": g["anchor_date"].max(),
                "pe": float((g["pe"] * g["w"]).sum() / wsum),
                "pb": float((g["pb"] * g["w"]).sum() / wsum),
                "n": int(len(g)),
                "w_cov": float(wsum),
                "incomplete": bool(g["incomplete"].any()),
            }
        )
    return pd.DataFrame(rows).sort_values("quarter_end")


def kline_fig(daily: pd.DataFrame) -> go.Figure:
    fig = go.Figure(
        data=[
            go.Candlestick(
                x=daily["date"],
                open=daily["open"],
                high=daily["high"],
                low=daily["low"],
                close=daily["close"],
                increasing_line_color="#ef5350",
                decreasing_line_color="#26a69a",
                name="HSTECH",
            )
        ]
    )
    fig.update_layout(
        title=None,
        template="plotly_dark",
        height=560,
        margin=dict(l=4, r=4, t=4, b=2),
        xaxis_rangeslider_visible=False,
        showlegend=False,
    )
    return fig


def val_fig(val: pd.DataFrame, index_daily: pd.DataFrame) -> go.Figure:
    # attach index quarter-end price
    prices = []
    for _, r in val.iterrows():
        q = pd.Timestamp(r["quarter_end"])
        last = pd.Timestamp(index_daily["date"].iloc[-1])
        if q > last:
            prices.append(float(index_daily.iloc[-1]["close"]))
        else:
            anc = month_end_close(index_daily, q)
            prices.append(anc[1] if anc else None)
    val = val.copy()
    val["price"] = prices
    fig = make_subplots(specs=[[{"secondary_y": True}]])
    fig.add_trace(
        go.Scatter(
            x=val["anchor_date"],
            y=val["pe"],
            mode="lines+markers",
            name="板块PE(加权)",
            line=dict(color="#ef5350", width=2),
        ),
        secondary_y=False,
    )
    fig.add_trace(
        go.Scatter(
            x=val["anchor_date"],
            y=val["pb"],
            mode="lines+markers",
            name="板块PB(加权)",
            line=dict(color="#61afef", width=1.5),
        ),
        secondary_y=False,
    )
    fig.add_trace(
        go.Scatter(
            x=val["anchor_date"],
            y=val["price"],
            mode="lines+markers",
            name="HSTECH季末点位",
            line=dict(color="#98c379", width=1.5),
        ),
        secondary_y=True,
    )
    if pd.notna(val["pe"].iloc[-1]):
        fig.add_hline(
            y=float(val["pe"].iloc[-1]),
            line_dash="dash",
            line_color="#e06c75",
            annotation_text="当前PE %.1f" % float(val["pe"].iloc[-1]),
            secondary_y=False,
        )
    fig.update_layout(
        title=None,
        template="plotly_dark",
        height=560,
        margin=dict(l=6, r=6, t=6, b=4),
        legend=dict(
            orientation="h", y=1.0, x=0, font=dict(size=10), bgcolor="rgba(0,0,0,0)"
        ),
        hovermode="x unified",
    )
    fig.update_yaxes(title_text="PE / PB", secondary_y=False)
    fig.update_yaxes(title_text="指数点位", secondary_y=True)
    return fig


def percentile(s: pd.Series, v: float | None) -> float | None:
    s = s.dropna()
    if s.empty or v is None or pd.isna(v):
        return None
    return float((s <= v).mean() * 100)


def render_episode(index_daily, val, k_html, v_html, meta_extra: dict) -> Path:
    sys.path.insert(0, str(ROOT / "tools/stock-analysis/src"))
    from render_report import _load_deck_template, _fmt

    last = val.iloc[-1]
    pe = float(last["pe"]) if pd.notna(last["pe"]) else None
    pb = float(last["pb"]) if pd.notna(last["pb"]) else None
    price = float(last["price"]) if pd.notna(last.get("price")) else float(
        index_daily.iloc[-1]["close"]
    )
    pe_pct = percentile(val["pe"], pe)
    pb_pct = percentile(val["pb"], pb)
    asof = pd.Timestamp(index_daily["date"].iloc[-1]).strftime("%Y-%m-%d")

    html = _load_deck_template()
    # strip fundamental chart page content — replace with coverage note panel
    fund_note = (
        "<div class='panel'><div class='note'>成分覆盖与口径</div>"
        "<div style='padding:12px;font-size:.85rem;line-height:1.6;color:#abb2bf'>"
        f"加权成分约 {int(last['n'])} 只，权重覆盖约 {last['w_cov']:.1f}%（检讨权重近似）。"
        "港股用「股东应占溢利」年化近似扣非；上一报告期盈利 + 本季末价（未结束用最新价）。"
        "成分随恒指检讨变化，历史点用当前权重回测，存在偏差。"
        "</div></div>"
    )
    reps = {
        "__NAME__": "恒生科技指数",
        "__CODE__": "HSTECH",
        "__ASOF__": asof,
        "__PRICE__": _fmt(price, 2),
        "__PE__": _fmt(pe, 1),
        "__PE_PCT__": _fmt(pe_pct, 1, "%"),
        "__PB__": _fmt(pb, 2),
        "__PB_PCT__": _fmt(pb_pct, 1, "%"),
        "__K__": k_html,
        "__F__": fund_note,
        "__V__": v_html,
    }
    # update scripts/titles for sector
    html = html.replace("封面要点", "板块封面")
    html = html.replace(
        "开场报名称与代码。&#10;点四个卡片：现价、动态市盈、市净、股息率。&#10;强调：数据仅供参考，先看结构再讲细节。",
        "本期板块：恒生科技指数 HSTECH。&#10;卡片：指数点位、板块PE、板块PB、历史分位。&#10;数据仅供参考。",
    )
    html = html.replace("行情结构", "指数走势")
    html = html.replace(
        "切到 K 线页，先停两秒让画面稳住。&#10;说明时间跨度：从上市以来到最新交易日，默认日线。&#10;再依次点周 / 月 / 季，看结构有没有变化——只描述高低与节奏。&#10;口播提示：语速放慢，手指别挡到中间安全带。&#10;本页不加结论，下一页再看财务趋势。",
        "看 HSTECH 指数 K 线。&#10;描述阶段高低，不预测。&#10;下一页说覆盖与口径。",
    )
    html = html.replace("财务趋势", "口径与覆盖")
    html = html.replace("季度营收与利润", "口径与覆盖")
    html = html.replace(
        "看单季营收与利润曲线。&#10;说明：累计已拆成单季，方便看趋势。&#10;指出最近几季变化，不做预测。",
        "说明：上季盈利年化 + 本季末价；港股用股东应占溢利近似扣非。&#10;交代成分权重覆盖。&#10;不做预测。",
    )
    html = html.replace("指标序列", "板块PE/PB")
    html = html.replace("指标序列 vs 现价", "板块 PE / PB / 点位")
    html = html.replace(
        "口径：上一季单季扣非×4 年化，配本季末收盘（未结束用最新价）。&#10;图含：季末股价、PE、PB。&#10;只比较位置，不给操作建议。",
        "图：HSTECH 季末点位 + 加权 PE + 加权 PB。&#10;对照当前 PE 分位。&#10;只比较位置。",
    )
    html = html.replace("最新交易日收盘", "指数最新点位")
    html = html.replace("动态PE · TTM扣非", "板块PE")
    html = html.replace("市净率 PB", "板块PB")
    html = html.replace("股息率", "权重覆盖")
    html = html.replace("__DIV__", f"{last['w_cov']:.0f}%")
    html = html.replace("__DIV_PCT__", f"n={int(last['n'])}")
    html = html.replace("近12月现金分红/现价 · 分位 __DIV_PCT__", "有效成分与权重")

    for k, v in reps.items():
        html = html.replace(k, str(v))

    OUT.mkdir(parents=True, exist_ok=True)
    path = OUT / "index.html"
    path.write_text(html, encoding="utf-8")
    meta = {
        "niche": "finance",
        "theme": "恒生科技板块PE",
        "date": date.today().isoformat(),
        "code": "HSTECH",
        "name": "恒生科技指数",
        "generated_at": datetime.now().isoformat(timespec="seconds"),
        "format": "9:16-ppt-deck",
        "pe_method": "prior_report_earnings_ann_x_quarter_end_price_weight_avg",
        "earnings_field": "股东应占溢利(年化，港股近似扣非)",
        **meta_extra,
    }
    (OUT / "meta.json").write_text(
        json.dumps(meta, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    return path


def main():
    CACHE.mkdir(parents=True, exist_ok=True)
    print("[1] index daily")
    index_daily = fetch_index_daily()
    index_daily.to_csv(CACHE / "index_daily.csv", index=False)
    print("  bars", len(index_daily), "last", index_daily["date"].iloc[-1].date())

    all_pts = []
    ok, fail = [], []
    for code, w in WEIGHTS.items():
        code = pad(code)
        print(f"[stock] {code} w={w}")
        try:
            daily = retry(lambda: fetch_stock_daily(code))
            time.sleep(0.5)
            fin = retry(lambda: fetch_earnings_equity(code))
            time.sleep(0.5)
            pts = stock_points(code, daily, fin)
            pts = retry(lambda: attach_shares_and_multiples(code, pts))
            time.sleep(0.4)
            if pts.empty or pts["pe"].dropna().empty:
                fail.append(code)
                print("  skip empty")
                continue
            pts.to_csv(CACHE / f"points_{code}.csv", index=False)
            all_pts.append(pts)
            ok.append(code)
            print("  points", len(pts), "last PE", round(float(pts["pe"].dropna().iloc[-1]), 1))
        except Exception as e:
            fail.append(code)
            print("  FAIL", type(e).__name__, e)

    if not all_pts:
        raise SystemExit("no constituent points")
    points = pd.concat(all_pts, ignore_index=True)
    points.to_csv(CACHE / "points_all.csv", index=False)
    val = aggregate(points, {pad(k): v for k, v in WEIGHTS.items()})
    # fill price from index
    prices = []
    for _, r in val.iterrows():
        q = pd.Timestamp(r["quarter_end"])
        last = pd.Timestamp(index_daily["date"].iloc[-1])
        if q > last:
            prices.append(float(index_daily.iloc[-1]["close"]))
        else:
            anc = month_end_close(index_daily, q)
            prices.append(anc[1] if anc else None)
    val["price"] = prices
    val.to_csv(CACHE / "sector_valuation.csv", index=False)
    print("[agg]", len(val), "last", val.tail(1).to_dict("records"))

    k_html = plot_offline(
        kline_fig(index_daily),
        output_type="div",
        include_plotlyjs=False,
        config={"displayModeBar": False, "responsive": True},
    )
    v_html = plot_offline(
        val_fig(val, index_daily),
        output_type="div",
        include_plotlyjs=False,
        config={"displayModeBar": False, "responsive": True},
    )
    path = render_episode(
        index_daily,
        val,
        k_html,
        v_html,
        {"constituents_ok": ok, "constituents_fail": fail},
    )
    print("DONE", path)
    print(path.resolve().as_uri())


if __name__ == "__main__":
    main()
