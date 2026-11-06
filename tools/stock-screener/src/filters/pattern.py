"""Sequential price/volume pattern filters (need row['_bars'])."""

from __future__ import annotations

from typing import Any

import pandas as pd

from indicators import kdj
from registry import register


def _ma_series(close: pd.Series, window: int) -> pd.Series:
    return close.rolling(window, min_periods=window).mean()


@register("ma10_ma60_volume_breakout")
def ma10_ma60_volume_breakout(row: dict[str, Any], params: dict[str, Any]) -> bool:
    """
    图形态（不再看 MA10）：
      1) 异动段：上涨日(红)多为放量、下跌日(绿)多为缩量
      2) 放量上涨收盘站上 MA60
      3) 之后回调：不破启动前最低点；默认也不破 MA60（可关）
      4) 回调相对异动日缩量（可用 max_pullback_vol_ratio 放宽）

    params:
      ma_slow: 60
      pre_days: 破位前用于定启动最低点的窗口 默认 20
      breakout_lookback: 异动破位距今最多天数 默认 25
      surge_days: 破位前用于红绿量对比的天数 默认 8
      min_breakout_pct: 破位日涨幅% 默认 2
      min_breakout_vol_ratio: 破位日量/前5日均量 默认 1.5
      red_green_vol_ratio: 红日均量/绿日均量 下限 默认 1.15
      require_above_ma60: 回调后是否必须站上 MA60 默认 true
      max_pullback_vol_ratio: 近几日均量/破位日量 上限 默认 0.85；<=0 表示不查
      pullback_days: 3
      kdj_j_max: 可选；不传则不查 KDJ
    """
    df = row.get("_bars")
    if df is None or not isinstance(df, pd.DataFrame) or df.empty:
        return False

    ma_slow_n = int(params.get("ma_slow", 60))
    # 兼容旧字段 trend_days
    pre_days = int(params.get("pre_days", params.get("trend_days", 20)))
    breakout_lookback = int(params.get("breakout_lookback", 25))
    surge_days = int(params.get("surge_days", 8))
    min_breakout_pct = float(params.get("min_breakout_pct", 2.0))
    min_vol_ratio = float(params.get("min_breakout_vol_ratio", 1.5))
    rg_ratio = float(params.get("red_green_vol_ratio", 1.15))
    require_ma60 = bool(params.get("require_above_ma60", True))
    max_pb_vol_ratio = float(params.get("max_pullback_vol_ratio", 0.85))
    pullback_days = int(params.get("pullback_days", 3))
    raw_j = params.get("kdj_j_max", None)
    check_kdj = raw_j is not None
    j_max = float(raw_j) if check_kdj else None

    need = ma_slow_n + pre_days + breakout_lookback + 5
    if len(df) < need:
        return False

    close = df["close"].astype(float)
    open_ = df["open"].astype(float)
    high = df["high"].astype(float)
    low = df["low"].astype(float)
    vol = df["volume"].astype(float)
    ma60 = _ma_series(close, ma_slow_n)

    j_now = None
    if check_kdj:
        kd = kdj(high, low, close)
        j_now = kd["j"].iloc[-1]
        if pd.isna(j_now) or float(j_now) >= j_max:
            return False

    c0 = float(close.iloc[-1])
    m0 = ma60.iloc[-1]
    if require_ma60 and (pd.isna(m0) or c0 < float(m0)):
        return False

    # --- 最近一次放量上穿 MA60 ---
    start = max(ma_slow_n + 1, len(df) - breakout_lookback)
    breakout_i = None
    for i in range(len(df) - 1, start - 1, -1):
        m = ma60.iloc[i]
        if pd.isna(m):
            continue
        c = float(close.iloc[i])
        c_prev = float(close.iloc[i - 1])
        # 收盘站上 60，前收在下
        if not (c >= float(m) and c_prev < float(m)):
            continue
        if c <= c_prev:  # 要上涨破位
            continue
        pct = (c / c_prev - 1.0) * 100.0 if c_prev else 0.0
        vol_ma = float(vol.iloc[max(0, i - 5) : i].mean()) if i >= 1 else 0.0
        vol_ok = vol_ma > 0 and float(vol.iloc[i]) >= vol_ma * min_vol_ratio
        pct_ok = pct >= min_breakout_pct
        if vol_ok or pct_ok:
            breakout_i = i
            break

    if breakout_i is None or breakout_i >= len(df) - 1:
        return False

    # --- 破位前窗口：只定启动最低点（不再看 MA10）---
    left = max(ma_slow_n, breakout_i - pre_days)
    pre = slice(left, breakout_i)
    if breakout_i - left < 3:
        return False
    swing_low = float(low.iloc[pre].min())

    # --- 异动段红放绿缩：破位日前 surge_days（含破位日）---
    s0 = max(left, breakout_i - surge_days + 1)
    red_vols: list[float] = []
    green_vols: list[float] = []
    for i in range(s0, breakout_i + 1):
        v = float(vol.iloc[i])
        # 红：收涨；绿：收跌
        if float(close.iloc[i]) >= float(close.iloc[i - 1]):
            red_vols.append(v)
        else:
            green_vols.append(v)
    if not red_vols:
        return False
    red_avg = sum(red_vols) / len(red_vols)
    green_avg = (sum(green_vols) / len(green_vols)) if green_vols else red_avg * 0.5
    if green_avg <= 0 or red_avg < green_avg * rg_ratio:
        return False

    # --- 破位后：不破最低点；默认不破 MA60；要有回撤；回调缩量 ---
    after_low = float(low.iloc[breakout_i:].min())
    if after_low < swing_low:  # 回调破了启动低点
        return False
    if c0 < swing_low:
        return False

    if require_ma60:
        for j in range(breakout_i, len(df)):
            mj = ma60.iloc[j]
            if pd.isna(mj) or float(close.iloc[j]) < float(mj):
                return False

    peak = float(high.iloc[breakout_i:].max())
    if c0 >= peak:  # 还在冲新高、未见回调
        return False

    b_vol = float(vol.iloc[breakout_i])
    if b_vol <= 0:
        return False
    if max_pb_vol_ratio > 0:
        recent_v = float(vol.iloc[-pullback_days:].mean())
        if recent_v > b_vol * max_pb_vol_ratio:
            return False

    row["pattern_breakout_i"] = int(breakout_i)
    row["pattern_breakout_date"] = str(pd.Timestamp(df.iloc[breakout_i]["date"]).date())
    row["pattern_swing_low"] = swing_low
    row["ma60"] = float(ma60.iloc[-1]) if pd.notna(ma60.iloc[-1]) else None
    if j_now is not None and pd.notna(j_now):
        row["kdj_j"] = float(j_now)
    return True


@register("accumulation_shrink_hold")
def accumulation_shrink_hold(row: dict[str, Any], params: dict[str, Any]) -> bool:
    """
    建仓缩量回踩（建仓中 / 建仓完成未起爆；排山顶诱多）：
      1) 前期箱体建仓（可多次上下沿反复）+ 点火/放量证据
      2) 相对箱体有过放量冲高
      3) 已缩量回踩，低点守住成本锚（VWAP；不必回到中轴以下）
      4) 现价仍在箱内或刚贴箱（未主升起爆）
      5) 落在箱体上沿且站上 VWAP（排箱底弱势假建仓）
      6) 峰值相对箱顶温和抬升（有试探、非山顶高潮）
      7) 排除贴死高点未缩量、下跌中继、深砸假缩量
    """
    df = row.get("_bars")
    if df is None or not isinstance(df, pd.DataFrame) or df.empty:
        return False

    box_min_days = int(params.get("box_min_days", 20))
    box_max_days = int(params.get("box_max_days", 50))
    box_width_min = float(params.get("box_width_min", 0.08))
    box_width_max = float(params.get("box_width_max", 0.22))
    min_up_dn_vol = float(params.get("min_up_dn_vol", 1.1))
    min_swings = int(params.get("min_swings", 2))
    # 箱内反复：触及上沿后回落到该分位即计一次（默认 0.7，不必跌破中轴）
    swing_reset_pos = float(params.get("swing_reset_pos", 0.70))
    ignite_vol_ratio = float(params.get("ignite_vol_ratio", 2.5))
    box_vs_quiet = float(params.get("box_vs_quiet", 1.15))
    quiet_days = int(params.get("quiet_days", 20))
    peak_lookback = int(params.get("peak_lookback", 30))
    lift_days = int(params.get("lift_days", 10))
    pullback_days = int(params.get("pullback_days", 5))
    max_pull_vol_ratio = float(params.get("max_pull_vol_ratio", 0.55))
    min_off_peak = float(params.get("min_off_peak", 0.03))
    cost_slack = float(params.get("cost_slack", 0.03))
    max_above_box = float(params.get("max_above_box", 0.08))
    # 冲高相对箱顶最大偏离；过大视为一波流高潮而非建仓后温和脱离
    max_peak_above_box = float(params.get("max_peak_above_box", 0.12))
    min_peak_above_box = float(params.get("min_peak_above_box", 0.0))
    # 建仓池：未起爆 + 箱上沿 + 站上成本未远离（回测用来压山顶诱多、抬破箱率）
    max_close_above_box = float(params.get("max_close_above_box", 0.0))
    min_box_pos = float(params.get("min_box_pos", 0.75))
    min_dist_cost = float(params.get("min_dist_cost", 0.03))
    max_dist_cost = float(params.get("max_dist_cost", 0.12))
    near_high_pct = float(params.get("near_high_pct", 0.95))
    exclude_vol_vs_lift = float(params.get("exclude_vol_vs_lift", 0.9))
    # 防顶部：峰到回踩低点的最大回撤（过大=砸下来后的假缩量）
    max_peak_drawdown = float(params.get("max_peak_drawdown", 0.20))
    # 防下跌中继：收盘在下行 MA60 下方，或均线下创新低
    reject_downtrend_relay = bool(params.get("reject_downtrend_relay", True))
    ma60_slope_lookback = int(params.get("ma60_slope_lookback", 10))
    ma60_slope_tol = float(params.get("ma60_slope_tol", 0.005))
    # 回踩期最低价不得跌破建仓箱下沿
    reject_break_box_low = bool(params.get("reject_break_box_low", True))

    need = quiet_days + box_max_days + peak_lookback + 5
    if len(df) < need:
        return False

    close = df["close"].astype(float)
    high = df["high"].astype(float)
    low = df["low"].astype(float)
    vol = df["volume"].astype(float)
    amount = df["amount"].astype(float)

    c0 = float(close.iloc[-1])
    n = len(df)

    # --- 在回看窗内找「放量冲高段」（最高 lift_days 均量），再相对它缩量 ---
    win0 = max(0, n - peak_lookback)
    search_lo = win0 + lift_days - 1
    search_hi = n - pullback_days - 1  # 冲高段须结束在回踩窗之前
    if search_hi < search_lo:
        return False

    roll = vol.rolling(lift_days, min_periods=lift_days).mean()
    seg = roll.iloc[search_lo : search_hi + 1]
    if seg.isna().all():
        return False
    markup_end = search_lo + int(seg.to_numpy().argmax())
    markup_start = markup_end - lift_days + 1
    markup_vol = float(roll.iloc[markup_end])
    if markup_vol <= 0:
        return False

    peak_i = markup_start + int(high.iloc[markup_start : markup_end + 1].to_numpy().argmax())
    peak = float(high.iloc[peak_i])
    # 冲高后至今的绝对高点（含二次冲高）
    peak_after = float(high.iloc[markup_start:].max())
    peak = max(peak, peak_after)

    if c0 >= peak * (1.0 - min_off_peak):
        return False

    recent_vol = float(vol.iloc[-pullback_days:].mean())
    pull_vol_ratio = recent_vol / markup_vol

    hi20 = float(high.iloc[-20:].max())
    near_high = hi20 > 0 and c0 >= hi20 * near_high_pct
    if pull_vol_ratio >= exclude_vol_vs_lift:
        return False
    if near_high:
        return False
    if pull_vol_ratio > max_pull_vol_ratio:
        return False

    if markup_end >= n - 1:
        return False
    pull_low = float(low.iloc[markup_end:].min())

    # --- 防顶部：高峰后深砸再缩量（非浅回踩建仓）---
    peak_dd = (peak - pull_low) / peak if peak > 0 else 1.0
    if peak_dd > max_peak_drawdown:
        return False

    # --- 防下跌中继：空头均线下的缩量歇脚 / 创新低 ---
    if reject_downtrend_relay and n >= 60 + ma60_slope_lookback:
        ma60 = float(close.iloc[-60:].mean())
        ma60_prev = float(close.iloc[-60 - ma60_slope_lookback : -ma60_slope_lookback].mean())
        ma60_down = ma60 < ma60_prev * (1.0 - ma60_slope_tol)
        if c0 < ma60 and ma60_down:
            return False
        prior_slice_end = max(0, n - max(pullback_days, 5))
        prior_slice_start = max(0, prior_slice_end - 60)
        if prior_slice_end > prior_slice_start:
            prior_low = float(low.iloc[prior_slice_start:prior_slice_end].min())
            if c0 < ma60 and pull_low <= prior_low * 1.001:
                return False

    # --- 冲高前寻找建仓箱（箱结束日可早于冲高起点若干日，避免粘上拉升段）---
    box_end_gap = int(params.get("box_end_gap", 15))
    box_end_hi = markup_start
    box_end_lo = max(box_min_days + quiet_days, markup_start - box_end_gap)
    if box_end_hi < box_min_days + quiet_days:
        return False

    best = None
    for box_end in range(box_end_hi, box_end_lo - 1, -2):
        max_blen = min(box_max_days, box_end - quiet_days)
        for blen in range(box_min_days, max_blen + 1, 2):
            b0 = box_end - blen
            if b0 < quiet_days:
                continue
            seg_h = high.iloc[b0:box_end]
            seg_l = low.iloc[b0:box_end]
            seg_c = close.iloc[b0:box_end]
            seg_v = vol.iloc[b0:box_end]
            seg_a = amount.iloc[b0:box_end]
            bh = float(seg_h.max())
            bl = float(seg_l.min())
            if bl <= 0:
                continue
            width = bh / bl - 1.0
            if width < box_width_min or width > box_width_max:
                continue

            up = (seg_c >= seg_c.shift(1)).fillna(True)
            up_vols = seg_v[up]
            dn_vols = seg_v[~up]
            if up_vols.empty:
                continue
            up_avg = float(up_vols.mean())
            dn_avg = float(dn_vols.mean()) if not dn_vols.empty else up_avg * 0.5
            if dn_avg <= 0 or up_avg < dn_avg * min_up_dn_vol:
                continue

            vwap = float(seg_a.sum() / seg_v.sum()) if float(seg_v.sum()) > 0 else float(seg_c.mean())
            # 成本锚用 VWAP；守住即可，回踩不必到中轴以下
            cost = vwap

            pos = (seg_c.astype(float) - bl) / (bh - bl)
            swings = 0
            touched_high = False
            for p in pos.tolist():
                if p >= 0.90:
                    touched_high = True
                elif touched_high and p <= swing_reset_pos:
                    swings += 1
                    touched_high = False

            quiet = vol.iloc[b0 - quiet_days : b0]
            quiet_avg = float(quiet.mean()) if len(quiet) == quiet_days else 0.0
            box_avg = float(seg_v.mean())
            look = vol.iloc[max(0, b0 - 5) : box_end]
            prior60 = vol.iloc[max(0, b0 - 60) : b0]
            prior60_avg = float(prior60.mean()) if len(prior60) >= 20 else quiet_avg
            ignite_ok = prior60_avg > 0 and float(look.max()) >= prior60_avg * ignite_vol_ratio
            elev_ok = quiet_avg > 0 and box_avg >= quiet_avg * box_vs_quiet
            if not (ignite_ok or elev_ok):
                continue
            need_swings = 1 if ignite_ok else min_swings
            if swings < need_swings:
                continue

            lift_high = float(high.iloc[markup_start : markup_end + 1].max())
            if lift_high < bl + 0.5 * (bh - bl):
                continue

            score = swings * 2.0 + (1.5 if ignite_ok else 0.0) + up_avg / dn_avg
            score -= abs(width - 0.12) * 5
            # 偏好箱体紧贴冲高前
            score -= 0.03 * (markup_start - box_end)
            cand = {
                "bh": bh,
                "bl": bl,
                "vwap": vwap,
                "cost": cost,
                "swings": swings,
                "score": score,
            }
            if best is None or cand["score"] > best["score"]:
                best = cand

    if best is None:
        return False

    cost = best["cost"]
    bh = best["bh"]
    bl = best["bl"]

    if pull_low < cost * (1.0 - cost_slack):
        return False
    if c0 < cost * (1.0 - cost_slack):
        return False
    if c0 < bl:
        return False
    if reject_break_box_low and pull_low < bl:
        return False

    # 关键：现价必须仍在建仓箱内（已越箱=拉升波/出货段，不是待起爆建仓）
    if c0 > bh * (1.0 + max_close_above_box):
        return False

    # 峰值相对箱顶：只允许温和试探；过大=高潮拉升已发生
    peak_above = peak / bh - 1.0 if bh > 0 else 0.0
    if peak_above > max_peak_above_box:
        return False
    # min_peak_above_box 默认 0：不强迫冲高（弱建仓可保留）
    if peak_above < min_peak_above_box:
        return False

    box_pos = (c0 - bl) / (bh - bl) if bh > bl else 0.0
    if box_pos < min_box_pos:
        return False

    dist_cost = c0 / cost - 1.0 if cost > 0 else 0.0
    # min_dist_cost=0 时允许贴成本（浮点略负不误杀）；>0 才要求明显站上成本
    if min_dist_cost > 0 and dist_cost < min_dist_cost:
        return False
    if dist_cost > max_dist_cost:
        return False

    # 防拉升波后出货：峰值已明显越出箱顶，再缩量回落（旧箱被甩在下面）
    # 箱内温和试探（peak_above 小）不触发，避免误杀好样本
    climax_left_box = float(params.get("climax_left_box", 0.10))
    if peak_above > climax_left_box and peak_dd > float(params.get("climax_pull_dd", 0.10)):
        return False

    row["pattern_box_low"] = bl
    row["pattern_box_high"] = bh
    row["pattern_vwap"] = best["vwap"]
    row["pattern_cost_anchor"] = cost
    row["pattern_pull_vol_ratio"] = float(pull_vol_ratio)
    row["pattern_swing_count"] = int(best["swings"])
    row["pattern_peak"] = peak
    row["pattern_pull_low"] = pull_low
    row["pattern_markup_vol"] = markup_vol
    row["pattern_peak_drawdown"] = float(peak_dd)
    row["pattern_box_pos"] = float(box_pos)
    row["pattern_peak_above_box"] = float(peak_above)
    row["pattern_dist_cost"] = float(dist_cost)
    row["pattern_peak_ext"] = float(peak / bh - 1.0) if bh else None
    return True


@register("ma60_shrink_pullback")
def ma60_shrink_pullback(row: dict[str, Any], params: dict[str, Any]) -> bool:
    """兼容旧配置 id。"""
    return ma10_ma60_volume_breakout(row, params)
