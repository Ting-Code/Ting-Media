#!/usr/bin/env python3
"""全 A 历史 PE、PB 分位筛选。按报告期全量拉取东财主要指标，再在本地算分位。

不生成录屏 HTML，也不为每只股票单独出图。
默认：双分位都 <=20%，且 PE、PB 有效点都 >=12。
"""

from __future__ import annotations

import argparse
import html
import json
import sys
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime
from pathlib import Path

import pandas as pd

SRC = Path(__file__).resolve().parents[1] / "src"
sys.path.insert(0, str(SRC))

from data_path import ensure_stock_data_on_path  # noqa: E402

ensure_stock_data_on_path()

from analysis import build_valuation_series, percentile, ytd_to_single_quarter  # noqa: E402
from cache_io import repo_root  # noqa: E402
from em_market_quarter import load_market_main_range, sync_market_main_range  # noqa: E402
from market import fetch_daily  # noqa: E402
from paths import tdx_vipdoc  # noqa: E402
from universe import build_universe  # noqa: E402

BOARD_CN = {"main": "主板", "chinext": "创业板", "star": "科创板", "bse": "北交所"}

def _tdx_hq_cache(vipdoc: str | Path) -> Path:
    return Path(vipdoc).resolve().parent / "T0002" / "hq_cache"


def load_tdx_industries(vipdoc: str | Path) -> dict[str, dict]:
    """本机通达信行业：一级 / 二级 / 三级。"""
    hq = _tdx_hq_cache(vipdoc)
    names: dict[str, str] = {}
    for fname in ("tdxzs3.cfg", "tdxzs.cfg"):
        path = hq / fname
        if not path.exists():
            continue
        for line in path.read_text(encoding="gbk", errors="replace").splitlines():
            parts = line.split("|")
            if len(parts) >= 6 and parts[5].startswith("X") and parts[0].strip():
                names.setdefault(parts[5].strip(), parts[0].strip())
    out: dict[str, dict] = {}
    hy = hq / "tdxhy.cfg"
    if not hy.exists():
        return out
    for line in hy.read_text(encoding="gbk", errors="replace").splitlines():
        parts = line.split("|")
        if len(parts) < 2:
            continue
        code = str(parts[1]).zfill(6)
        tag = parts[5].strip() if len(parts) > 5 else ""
        l1 = l2 = l3 = ""
        if tag.startswith("X"):
            if len(tag) >= 3:
                l1 = names.get(tag[:3], "")
            if len(tag) >= 5:
                l2 = names.get(tag[:5], "")
            if len(tag) >= 7:
                l3 = names.get(tag[:7], names.get(tag, ""))
        out[code] = {"industry_l1": l1, "industry_l2": l2, "industry_l3": l3}
    return out


def _attach_industries(df: pd.DataFrame, vipdoc: str | Path) -> pd.DataFrame:
    if df is None or df.empty:
        for col in ("industry_l1", "industry_l2", "industry_l3"):
            df[col] = None
        return df
    mapping = load_tdx_industries(vipdoc)
    codes = df["code"].astype(str).str.zfill(6)
    df = df.copy()
    df["code"] = codes
    for col in ("industry_l1", "industry_l2", "industry_l3"):
        df[col] = codes.map(lambda c, col=col: (mapping.get(c) or {}).get(col) or None)
    return df



def _num(v, nd=2):
    if v is None or (isinstance(v, float) and pd.isna(v)):
        return None
    try:
        if pd.isna(v):
            return None
    except TypeError:
        pass
    return round(float(v), nd)


def _panel_from_market(g: pd.DataFrame) -> pd.DataFrame:
    g = g.sort_values("REPORT_DATE").drop_duplicates("REPORT_DATE", keep="last").copy()
    df = pd.DataFrame(
        {
            "REPORT_DATE": pd.to_datetime(g["REPORT_DATE"]),
            "DEDUCT_PARENT_NETPROFIT": pd.to_numeric(g.get("KCFJCXSYJLR"), errors="coerce"),
            "PARENT_NETPROFIT": pd.to_numeric(g.get("PARENTNETPROFIT"), errors="coerce"),
            "TOTAL_OPERATE_INCOME": pd.to_numeric(g.get("TOTALOPERATEREVE"), errors="coerce"),
            "SHARE_CAPITAL": pd.to_numeric(g.get("TOTAL_SHARE"), errors="coerce"),
            "BPS": pd.to_numeric(g.get("BPS"), errors="coerce"),
        }
    )
    df["TOTAL_PARENT_EQUITY"] = df["BPS"] * df["SHARE_CAPITAL"]
    df = df.dropna(subset=["REPORT_DATE", "DEDUCT_PARENT_NETPROFIT"])
    if df.empty:
        return df
    df = df.set_index("REPORT_DATE").sort_index()
    for col, new in [
        ("TOTAL_OPERATE_INCOME", "revenue_q"),
        ("PARENT_NETPROFIT", "parent_np_q"),
        ("DEDUCT_PARENT_NETPROFIT", "deduct_np_q"),
    ]:
        df[new] = ytd_to_single_quarter(df[col])
    df["deduct_np_ttm"] = df["deduct_np_q"].rolling(4).sum()
    df["revenue_ttm"] = df["revenue_q"].rolling(4).sum()
    return df.reset_index()


def _analyze_one(item: dict, panel: pd.DataFrame | None) -> dict:
    code = item["code"]
    name = item.get("name") or code
    board = item.get("board") or ""
    row = {
        "code": code,
        "name": name,
        "board": BOARD_CN.get(board, board),
        "asof": None,
        "price": None,
        "pe": None,
        "pe_percentile": None,
        "pe_points": 0,
        "pb": None,
        "pb_percentile": None,
        "pb_points": 0,
        "report_date": None,
        "error": None,
    }
    try:
        if panel is None or panel.empty:
            row["error"] = "无财务"
            return row
        daily = fetch_daily(code, start_date="2015-01-01", adjust="bfq")
        if daily is None or daily.empty:
            row["error"] = "无日线"
            return row
        series = build_valuation_series(panel, daily, pd.DataFrame())
        last = daily.iloc[-1]
        row["asof"] = str(pd.Timestamp(last["date"]))[:10]
        row["price"] = _num(last["close"], 2)
        if series is None or series.empty:
            return row
        snap = series.iloc[-1]
        pe = snap.get("pe")
        pb = snap.get("pb")
        if pe is not None and pd.isna(pe):
            pe = None
        if pb is not None and pd.isna(pb):
            pb = None
        row["pe"] = _num(pe, 2)
        row["pb"] = _num(pb, 2)
        prev = snap.get("prev_report_date")
        row["report_date"] = None if prev is None or pd.isna(prev) else str(pd.Timestamp(prev))[:10]
        pe_s = series["pe"]
        pb_s = series["pb"]
        row["pe_points"] = int(pe_s.notna().sum())
        row["pb_points"] = int(pb_s.notna().sum())
        row["pe_percentile"] = _num(percentile(pe_s, pe), 1)
        row["pb_percentile"] = _num(percentile(pb_s, pb), 1)
        return row
    except Exception as exc:
        row["error"] = f"{type(exc).__name__}: {exc}"
        return row


def _has_error(v) -> bool:
    if v is None:
        return False
    try:
        if pd.isna(v):
            return False
    except TypeError:
        pass
    s = str(v).strip()
    return s not in {"", "nan", "None", "NaN"}


def _is_hit(row: dict, pe_max: float, pb_max: float, min_points: int) -> bool:
    if _has_error(row.get("error")):
        return False
    if row.get("pe") is None or row.get("pb") is None:
        return False
    if row.get("pe_percentile") is None or row.get("pb_percentile") is None:
        return False
    if int(row.get("pe_points") or 0) < min_points or int(row.get("pb_points") or 0) < min_points:
        return False
    return float(row["pe_percentile"]) <= pe_max and float(row["pb_percentile"]) <= pb_max


def _write_html(out_dir: Path, hits: pd.DataFrame, meta: dict) -> None:
    def cell(v, nd=None, suffix=""):
        if v is None or (isinstance(v, float) and pd.isna(v)):
            return "—"
        if nd is not None:
            try:
                v = f"{float(v):.{nd}f}"
            except (TypeError, ValueError):
                return "—"
        return html.escape(str(v) + suffix)

    rows = []
    for i, r in enumerate(hits.to_dict("records"), 1):
        rows.append(
            "<tr>"
            f"<td class='num'>{i}</td>"
            f"<td>{cell(r.get('code'))}</td>"
            f"<td>{cell(r.get('name'))}</td>"
            f"<td>{cell(r.get('board'))}</td>"
            f"<td>{cell(r.get('industry_l1'))}</td>"
            f"<td>{cell(r.get('industry_l2'))}</td>"
            f"<td>{cell(r.get('industry_l3'))}</td>"
            f"<td class='num' data-v='{r.get('price')}'>{cell(r.get('price'), 2)}</td>"
            f"<td class='num' data-v='{r.get('pe')}'>{cell(r.get('pe'), 2)}</td>"
            f"<td class='num' data-v='{r.get('pe_percentile')}'>{cell(r.get('pe_percentile'), 1, '%')}</td>"
            f"<td class='num' data-v='{r.get('pe_points')}'>{cell(r.get('pe_points'))}</td>"
            f"<td class='num' data-v='{r.get('pb')}'>{cell(r.get('pb'), 2)}</td>"
            f"<td class='num' data-v='{r.get('pb_percentile')}'>{cell(r.get('pb_percentile'), 1, '%')}</td>"
            f"<td class='num' data-v='{r.get('pb_points')}'>{cell(r.get('pb_points'))}</td>"
            f"<td>{cell(r.get('report_date'))}</td>"
            "</tr>"
        )
    body = "\n".join(rows) or "<tr><td colspan='15'>没有符合条件的股票。</td></tr>"
    asof = html.escape(str(meta.get("asof") or ""))
    title = f"全A 历史PE、PB低分位（{asof}）"
    lead = (
        f"样本为通达信全A（沪深京，已排除指数和ST），共 {meta.get('universe')} 只；"
        f"行情日 {asof}。"
        f"口径：观察季末价 ÷ 上一季单季扣非×4 得PE，同期市净率；"
        f"分位为该股官方序列上「小于等于当前值」的占比（含未完成季）。"
        f"财务数据按报告期全量拉取东财主要指标。行业分类来自本机通达信。"
        f"入选条件：PE、PB 分位均 ≤{meta.get('pe_max')}%，且有效点均 ≥{meta.get('min_points')}。"
        f"命中 {meta.get('hits')} 只。亏损或扣非为零的PE留空，不计入低分位。"
        "本页仅为参考，不构成投资建议。"
    )
    page = f"""<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{html.escape(title)}</title>
<style>
  :root {{ --bg:#f6f3ee; --card:#fff; --ink:#1c1916; --muted:#6b645c; --line:#e6e0d6; --accent:#8b1e2d; }}
  * {{ box-sizing:border-box; }}
  body {{ margin:0; background:var(--bg); color:var(--ink); font:15px/1.55 "Source Han Sans SC","Noto Sans SC","PingFang SC","Microsoft YaHei",sans-serif; }}
  main {{ max-width:1180px; margin:0 auto; padding:32px 24px 64px; }}
  h1 {{ font-size:26px; font-weight:650; margin:0 0 12px; }}
  .lead {{ color:var(--muted); margin:0 0 20px; max-width:72em; }}
  .meta {{ display:flex; flex-wrap:wrap; gap:8px 16px; margin:0 0 20px; color:var(--muted); font-size:13px; }}
  .meta b {{ color:var(--ink); font-weight:600; }}
  .wrap {{ background:var(--card); border:1px solid var(--line); border-radius:12px; overflow:auto; }}
  table {{ border-collapse:collapse; width:100%; min-width:960px; }}
  th, td {{ padding:8px 10px; border-bottom:1px solid var(--line); text-align:left; white-space:nowrap; }}
  th {{ position:sticky; top:0; background:#faf8f4; font-weight:600; cursor:pointer; user-select:none; }}
  th:hover {{ color:var(--accent); }}
  td.num, th.num {{ text-align:right; font-variant-numeric:tabular-nums; }}
  tbody tr:hover {{ background:#f3efe8; }}
  footer {{ margin-top:18px; color:var(--muted); font-size:12px; }}
</style>
</head>
<body>
<main>
  <h1>{html.escape(title)}</h1>
  <p class="lead">{html.escape(lead)}</p>
  <div class="meta">
    <span>样本 <b>{meta.get('universe')}</b></span>
    <span>算完 <b>{meta.get('done')}</b></span>
    <span>命中 <b>{meta.get('hits')}</b></span>
    <span>失败 <b>{meta.get('errors')}</b></span>
    <span>有效点不足 <b>{meta.get('too_few_points')}</b></span>
    <span>PE 或 PB 为空 <b>{meta.get('blank_valuation')}</b></span>
  </div>
  <div class="wrap">
    <table id="t">
      <thead>
        <tr>
          <th class="num">#</th>
          <th>代码</th><th>名称</th><th>上市板</th><th>一级行业</th><th>二级行业</th><th>三级行业</th>
          <th class="num">收盘</th>
          <th class="num">PE</th><th class="num">PE分位</th><th class="num">PE点数</th>
          <th class="num">PB</th><th class="num">PB分位</th><th class="num">PB点数</th>
          <th>业绩期</th>
        </tr>
      </thead>
      <tbody>
        {body}
      </tbody>
    </table>
  </div>
  <footer>完整结果见同目录 all.csv；本页名单仅供参考，不构成投资建议。</footer>
</main>
<script>
(function() {{
  const table = document.getElementById("t");
  const ths = [...table.tHead.rows[0].cells];
  let idx = 5, dir = 1;
  function val(td) {{
    const raw = td.getAttribute("data-v");
    if (raw !== null && raw !== "None" && raw !== "") {{
      const n = Number(raw);
      if (!Number.isNaN(n)) return n;
    }}
    return td.textContent.trim();
  }}
  function sortBy(col, toggle) {{
    if (toggle) dir = (idx === col) ? -dir : 1;
    idx = col;
    const tb = table.tBodies[0];
    const rows = [...tb.rows];
    rows.sort((a, b) => {{
      const av = val(a.cells[col]), bv = val(b.cells[col]);
      if (typeof av === "number" && typeof bv === "number") return (av - bv) * dir;
      return String(av).localeCompare(String(bv), "zh") * dir;
    }});
    rows.forEach((r, i) => {{ r.cells[0].textContent = i + 1; tb.appendChild(r); }});
    ths.forEach((th, i) => th.dataset.sort = i === col ? (dir > 0 ? "asc" : "desc") : "");
  }}
  ths.forEach((th, i) => th.addEventListener("click", () => sortBy(i, true)));
  sortBy(5, false);
}})();
</script>
</body>
</html>
"""
    (out_dir / "index.html").write_text(page, encoding="utf-8")


def main() -> int:
    ap = argparse.ArgumentParser(description="全A 历史PE、PB低分位筛选（不是录屏 HTML）")
    ap.add_argument("--pe-max", type=float, default=20.0)
    ap.add_argument("--pb-max", type=float, default=20.0)
    ap.add_argument("--min-points", type=int, default=12)
    ap.add_argument("--workers", type=int, default=8, help="本地计算并发")
    ap.add_argument("--fetch-workers", type=int, default=3, help="按季拉取并发")
    ap.add_argument("--vipdoc", default=None)
    ap.add_argument("--limit", type=int, default=0)
    ap.add_argument("--refresh-financials", action="store_true")
    args = ap.parse_args()

    vipdoc = args.vipdoc or tdx_vipdoc()
    if not vipdoc:
        print("找不到通达信 vipdoc", file=sys.stderr)
        return 2

    t0 = time.time()
    sync_market_main_range(workers=args.fetch_workers, force=args.refresh_financials)
    market = load_market_main_range()
    print(f"market rows={len(market)} codes={market['SECURITY_CODE'].nunique() if not market.empty else 0}", flush=True)
    panels: dict[str, pd.DataFrame] = {}
    if not market.empty:
        for code, g in market.groupby("SECURITY_CODE", sort=False):
            panels[str(code).zfill(6)] = _panel_from_market(g)

    universe = build_universe(
        vipdoc,
        {"boards": ["main", "chinext", "star", "bse"], "exclude_index": True, "exclude_st": True},
    )
    if args.limit and args.limit > 0:
        universe = universe[: args.limit]
    print(
        f"universe={len(universe)} panels={len(panels)} workers={args.workers} "
        f"pe<= {args.pe_max} pb<= {args.pb_max} min_points={args.min_points}",
        flush=True,
    )

    staging = repo_root() / "cache" / "pe_pb_low_running"
    staging.mkdir(parents=True, exist_ok=True)
    progress_path = staging / "progress.jsonl"
    if progress_path.exists():
        progress_path.unlink()

    rows: list[dict] = []
    t1 = time.time()
    done = 0
    with ThreadPoolExecutor(max_workers=max(1, args.workers)) as pool:
        futs = {pool.submit(_analyze_one, item, panels.get(item["code"])): item["code"] for item in universe}
        for fut in as_completed(futs):
            row = fut.result()
            rows.append(row)
            done += 1
            with progress_path.open("a", encoding="utf-8") as fh:
                fh.write(json.dumps(row, ensure_ascii=False) + "\n")
            if done % 200 == 0 or done == len(universe):
                elapsed = time.time() - t1
                rate = done / elapsed if elapsed else 0
                eta = (len(universe) - done) / rate if rate else 0
                n_err = sum(1 for r in rows if r.get("error"))
                print(
                    f"{done}/{len(universe)} {rate:.1f}/s eta={eta/60:.1f}m errors={n_err} last={row.get('code')} {row.get('name')}",
                    flush=True,
                )

    df = pd.DataFrame(rows)
    df = _attach_industries(df, vipdoc)
    asofs = df["asof"].dropna() if not df.empty else pd.Series(dtype=object)
    asof = str(asofs.mode().iloc[0]) if not asofs.empty else datetime.now().strftime("%Y-%m-%d")
    hits_mask = df.apply(lambda r: _is_hit(r.to_dict(), args.pe_max, args.pb_max, args.min_points), axis=1) if not df.empty else pd.Series(dtype=bool)
    df["hit"] = hits_mask
    hits = df[hits_mask].copy() if not df.empty else df
    if not hits.empty:
        hits = hits.sort_values(["pe_percentile", "pb_percentile", "code"]).reset_index(drop=True)

    def _blank_err(s):
        return s.isna() | (s.astype(str).str.strip() == "") | (s.astype(str) == "None")

    no_err = _blank_err(df["error"]) if not df.empty else pd.Series(dtype=bool)
    too_few = int((no_err & ((df["pe_points"] < args.min_points) | (df["pb_points"] < args.min_points))).sum()) if not df.empty else 0
    blank_val = int((no_err & (df["pe"].isna() | df["pb"].isna()) & (df["pe_points"] >= args.min_points) & (df["pb_points"] >= args.min_points)).sum()) if not df.empty else 0
    n_err = int((~no_err).sum()) if not df.empty else 0

    meta = {
        "asof": asof,
        "universe": int(len(universe)),
        "done": int(len(df)),
        "hits": int(len(hits)),
        "errors": n_err,
        "too_few_points": too_few,
        "blank_valuation": blank_val,
        "pe_max": args.pe_max,
        "pb_max": args.pb_max,
        "min_points": args.min_points,
        "workers": args.workers,
        "fetch_workers": args.fetch_workers,
        "financial_source": "eastmoney_market_main_quarter",
        "elapsed_sec": round(time.time() - t0, 1),
        "vipdoc": str(vipdoc),
    }
    out_dir = repo_root() / "cache" / f"pe_pb_low_{asof}"
    out_dir.mkdir(parents=True, exist_ok=True)
    cols = [
        "code", "name", "board", "industry_l1", "industry_l2", "industry_l3",
        "asof", "price", "pe", "pe_percentile", "pe_points",
        "pb", "pb_percentile", "pb_points", "report_date", "hit", "error",
    ]
    for c in cols:
        if c not in df.columns:
            df[c] = None
    df["code"] = df["code"].astype(str).str.zfill(6)
    if not hits.empty:
        hits["code"] = hits["code"].astype(str).str.zfill(6)
    df[cols].to_csv(out_dir / "all.csv", index=False, encoding="utf-8-sig")
    hits_cols = [c for c in cols if c != "error"]
    out_hits = hits[hits_cols] if not hits.empty else pd.DataFrame(columns=hits_cols)
    out_hits.to_csv(out_dir / "hits.csv", index=False, encoding="utf-8-sig")
    (out_dir / "meta.json").write_text(json.dumps(meta, ensure_ascii=False, indent=2), encoding="utf-8")
    err_df = df[~no_err][cols] if not df.empty else pd.DataFrame(columns=cols)
    err_df.to_csv(out_dir / "errors.csv", index=False, encoding="utf-8-sig")
    _write_html(out_dir, out_hits, meta)
    print(json.dumps(meta, ensure_ascii=False, indent=2), flush=True)
    print(out_dir / "index.html", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())