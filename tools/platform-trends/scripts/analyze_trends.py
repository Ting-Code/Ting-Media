"""Fetch Bilibili / Weibo / Douyin hot boards and summarize.

Default: print data summary only (no HTML).
Optional: --html to write a 9:16 episode deck when explicitly making a recording episode.

Usage:
  python scripts/analyze_trends.py
  python scripts/analyze_trends.py --platform bilibili,weibo
  python scripts/analyze_trends.py --html --theme TODAY --date YYYY-MM-DD
"""
from __future__ import annotations

import argparse
import json
import sys
from datetime import date, datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT.parent / "stock-analysis" / "src"))
sys.path.insert(0, str(ROOT / "src"))

from analyze import FetchResult, TrendReport, analyze  # noqa: E402
from fetch_bilibili import fetch_bilibili  # noqa: E402
from fetch_douyin import fetch_douyin  # noqa: E402
from fetch_weibo import fetch_weibo  # noqa: E402

FETCHERS = {
    "bilibili": fetch_bilibili,
    "weibo": fetch_weibo,
    "douyin": fetch_douyin,
}
PLATFORM_LABEL = {"bilibili": "B站", "weibo": "微博", "douyin": "抖音"}

def fetch_all(platforms: list[str]) -> list[FetchResult]:
    results: list[FetchResult] = []
    for name in platforms:
        fn = FETCHERS[name]
        print("[fetch]", name)
        try:
            items = fn()
            print("  ok", len(items))
            results.append(FetchResult(platform=name, items=items))
        except Exception as exc:  # noqa: BLE001
            msg = str(exc)
            print("  FAIL", msg)
            results.append(FetchResult(platform=name, items=[], error=msg))
    return results

def fmt_count(value) -> str:
    if value is None:
        return "-"
    number = float(value)
    if abs(number) >= 10000:
        return (("%.2f" % (number / 10000)).rstrip("0").rstrip(".")) + "万"
    if abs(number - round(number)) < 1e-6:
        return str(int(round(number)))
    return "%.1f" % number

def print_summary(report: TrendReport, *, asof: str, top_n: int = 10) -> None:
    print()
    print("=== 跨平台热度摘要", asof, "===")
    print("成功", report.summary["ok_count"], "家 · 失败", report.summary["fail_count"], "家 · 条目", report.summary["total_items"])
    print("小红书/视频号未接入；热度不跨平台换算。")
    print()
    for result in report.results:
        label = PLATFORM_LABEL.get(result.platform, result.platform)
        if result.error:
            print("#", label, "FAIL:", result.error)
            print()
            continue
        kind = "作品" if result.platform == "bilibili" else "话题/热词"
        print("#", label, "·", len(result.items), kind)
        for item in result.items[:top_n]:
            rank = item.rank if item.rank is not None else "-"
            bits = [str(rank), item.title]
            if item.author:
                bits.append(item.author)
            if item.niche and item.niche != "未标注":
                bits.append(item.niche)
            if item.heat is not None:
                bits.append(fmt_count(item.heat))
            print(" -", " | ".join(bits))
        print()
    if report.bilibili_niches:
        print("# B站分区 Top")
        for row in report.bilibili_niches[:8]:
            print(" -", row["niche"], "·", row["works"], "条 · 播放", fmt_count(row["views"]), "· 点赞", fmt_count(row["likes"]))
        print()
    if report.weibo_niches:
        print("# 微博分类")
        for row in report.weibo_niches[:8]:
            print(" -", row["niche"], "·", row["topics"], "条")
        print()
    if report.overlaps:
        print("# 跨平台标题重合", "(top", min(8, len(report.overlaps)), ")")
        for row in report.overlaps[:8]:
            plats = " x ".join(PLATFORM_LABEL.get(p, p) for p in row["platforms"])
            titles = " / ".join(row["titles"][p] for p in row["platforms"])
            print(" -", plats + ":", titles)
        print()
    print("生成数据仅供参考，不构成任何决策依据。")

def write_cache(report: TrendReport, out_dir: Path, *, asof: str, platforms: list[str]) -> Path:
    out_dir.mkdir(parents=True, exist_ok=True)
    for result in report.results:
        payload = {
            "platform": result.platform,
            "error": result.error,
            "items": [it.to_dict() for it in result.items],
        }
        (out_dir / (result.platform + ".json")).write_text(
            json.dumps(payload, ensure_ascii=False, indent=2) + chr(10), encoding="utf-8"
        )
    analysis = {
        "asof": asof,
        "platforms": platforms,
        "bilibili_niches": report.bilibili_niches,
        "weibo_niches": report.weibo_niches,
        "overlaps": report.overlaps,
        "summary": report.summary,
    }
    path = out_dir / "analysis.json"
    path.write_text(json.dumps(analysis, ensure_ascii=False, indent=2) + chr(10), encoding="utf-8")
    return path

def write_html(*, theme: str, day: date, niche: str, report: TrendReport, asof: str, platforms: list[str], media_root: Path | None) -> Path:
    from episode_path import episode_dir
    from render_report import render_html

    ep = episode_dir(niche=niche, theme=theme, day=day, media_root=media_root)
    ep.mkdir(parents=True, exist_ok=True)
    cache = ep / "cache"
    cache.mkdir(parents=True, exist_ok=True)
    write_cache(report, cache, asof=asof, platforms=platforms)
    out = render_html(theme=theme, asof=asof, report=report, out_path=ep / "index.html")
    meta = {
        "niche": niche,
        "theme": theme,
        "date": day.isoformat(),
        "platforms": platforms,
        "asof": asof,
        "generated_at": datetime.now().isoformat(timespec="seconds"),
        "html": "index.html",
        "format": "9:16-ppt-deck",
        "data_tool": "tools/platform-trends",
        "summary": report.summary,
    }
    (ep / "meta.json").write_text(json.dumps(meta, ensure_ascii=False, indent=2) + chr(10), encoding="utf-8")
    return out

def run(*, platforms: list[str], top_n: int, write_json: bool, html: bool, theme: str, day: date, niche: str, media_root: Path | None = None) -> TrendReport:
    results = fetch_all(platforms)
    report = analyze(results)
    asof = datetime.now().strftime("%Y-%m-%d %H:%M")
    print_summary(report, asof=asof, top_n=top_n)
    if write_json:
        out_dir = ROOT / "output" / day.isoformat()
        path = write_cache(report, out_dir, asof=asof, platforms=platforms)
        print("[json]", path)
    if html:
        path = write_html(theme=theme, day=day, niche=niche, report=report, asof=asof, platforms=platforms, media_root=media_root)
        print("[html]", path)
        print("Open in browser:", path.resolve().as_uri())
    return report

def main() -> None:
    parser = argparse.ArgumentParser(description="跨平台热度：B站/微博/抖音（免 Key）；默认只摘要数据")
    parser.add_argument("--platform", default="bilibili,weibo,douyin", help="comma list: bilibili,weibo,douyin")
    parser.add_argument("--top", type=int, default=10, help="each platform top N in console")
    parser.add_argument("--json", action="store_true", help="write analysis JSON under output/")
    parser.add_argument("--html", action="store_true", help="also write 9:16 episode HTML (recording only)")
    parser.add_argument("--theme", default="今日热度", help="episode theme (with --html)")
    parser.add_argument("--date", default="", help="archive date YYYY-MM-DD")
    parser.add_argument("--niche", default="trends", help="episodes dir name (with --html)")
    args = parser.parse_args()
    platforms = [p.strip() for p in args.platform.split(",") if p.strip()]
    unknown = [p for p in platforms if p not in FETCHERS]
    if unknown:
        raise SystemExit("unknown platform: " + ",".join(unknown))
    if not platforms:
        raise SystemExit("no platform selected")
    day = date.fromisoformat(args.date) if args.date else date.today()
    run(
        platforms=platforms,
        top_n=max(1, args.top),
        write_json=bool(args.json or args.html),
        html=bool(args.html),
        theme=args.theme.strip() or "今日热度",
        day=day,
        niche=args.niche.strip() or "trends",
    )

if __name__ == "__main__":
    main()
