# -*- coding: utf-8 -*-
"""CLI: generate / validate / pack offline interactive HTML into episode folders."""
from __future__ import annotations

import argparse
import json
import sys
from datetime import date
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
MEDIA_ROOT = ROOT.parents[1]
SCREEN_SRC = ROOT.parent / "screen-pack" / "src"
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
if str(SCREEN_SRC) not in sys.path:
    sys.path.insert(0, str(SCREEN_SRC))

from src.generate import generate, load_content_file  # noqa: E402
from src.pack import build_zip  # noqa: E402
from src.specs import PLATFORMS, load_specs  # noqa: E402
from src.validate import format_report, validate_dir  # noqa: E402


def _resolve_episode_out(args: argparse.Namespace, data: dict) -> tuple[Path, Path | None]:
    """Return (pack_dir, zip_path). Episode mode puts everything under one episode folder."""
    if getattr(args, "out", None):
        out = Path(args.out)
        z = Path(args.zip) if getattr(args, "zip", None) else None
        return out, z

    from episode_path import episode_dir

    theme = (getattr(args, "theme", None) or "").strip() or str(data.get("title") or "互动页")
    day = date.fromisoformat(args.date) if getattr(args, "date", None) else date.today()
    niche = (getattr(args, "niche", None) or "finance").strip() or "finance"
    ep = episode_dir(niche=niche, theme=theme, day=day, media_root=MEDIA_ROOT)
    ep.mkdir(parents=True, exist_ok=True)

    # keep recording index.html free; interactive assets live in subfolder
    pack_dir = ep / "interactive"
    plat = args.platform if args.platform != "common" else "common"
    if args.single:
        pack_dir = ep / f"interactive-{plat}-single"
        zpath = ep / f"interactive-{plat}-single.zip"
    else:
        zpath = ep / f"interactive-{plat}.zip"
    return pack_dir, zpath


def cmd_specs(_: argparse.Namespace) -> int:
    print(json.dumps(load_specs(), ensure_ascii=False, indent=2))
    return 0


def cmd_validate(args: argparse.Namespace) -> int:
    report = validate_dir(Path(args.path), platform=args.platform)
    print(format_report(report))
    return 0 if report.ok else 1


def cmd_generate(args: argparse.Namespace) -> int:
    data = load_content_file(Path(args.content))
    out, zpath = _resolve_episode_out(args, data)
    # explicit --zip overrides episode default
    if getattr(args, "zip", None):
        zpath = Path(args.zip)

    generate(data, out, platform=args.platform, single_file=args.single)
    report = validate_dir(out, platform=args.platform)
    print(f"generated -> {out}")
    print(format_report(report))

    # merge into episode meta.json if we are inside an episode folder
    ep = out.parent
    if (ep / "meta.json").exists() or out.name.startswith("interactive"):
        meta_path = ep / "meta.json"
        meta = {}
        if meta_path.is_file():
            try:
                meta = json.loads(meta_path.read_text(encoding="utf-8"))
            except json.JSONDecodeError:
                meta = {}
        packs = meta.get("interactive") if isinstance(meta.get("interactive"), dict) else {}
        key = args.platform + ("-single" if args.single else "")
        packs[key] = {
            "dir": out.name,
            "zip": zpath.name if zpath else None,
            "platform": args.platform,
            "single_file": bool(args.single),
        }
        meta["interactive"] = packs
        if "html" not in meta:
            # recording deck may be added later by screen-pack / platform-trends
            meta.setdefault("niche", getattr(args, "niche", None) or "finance")
            meta.setdefault("theme", getattr(args, "theme", None) or data.get("title"))
            meta.setdefault("date", getattr(args, "date", None) or date.today().isoformat())
        meta_path.write_text(json.dumps(meta, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        print(f"meta -> {meta_path}")

    do_zip = zpath is not None and not getattr(args, "no_zip", False)
    if do_zip and zpath is not None:
        build_zip(out, zpath, platform=args.platform, strict=not args.force)
        print(f"zip -> {zpath} ({zpath.stat().st_size} bytes)")
    return 0 if report.ok or args.force else 1


def cmd_pack(args: argparse.Namespace) -> int:
    z = build_zip(Path(args.path), Path(args.zip), platform=args.platform, strict=not args.force)
    print(f"zip -> {z} ({z.stat().st_size} bytes)")
    print(format_report(validate_dir(Path(args.path), platform=args.platform)))
    return 0


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(
        description="Offline interactive HTML → episodes/<赛道>/YYYY-MM-DD_主题/"
    )
    p.add_argument(
        "--platform",
        default="common",
        choices=["common", *PLATFORMS],
        help="校验/生成目标平台（common=三端交集）",
    )
    sub = p.add_subparsers(dest="cmd", required=True)

    s = sub.add_parser("specs", help="打印内置平台规范 JSON")
    s.set_defaults(func=cmd_specs)

    s = sub.add_parser("validate", help="校验目录是否符合平台规范")
    s.add_argument("path", help="含 index.html 的目录")
    s.set_defaults(func=cmd_validate)

    s = sub.add_parser("generate", help="生成离线包（默认写入一期 episodes 目录）")
    s.add_argument("--content", required=True, help="内容 JSON 路径")
    s.add_argument("--theme", default="", help="节目主题；默认用 content.title")
    s.add_argument("--date", default="", help="节目日期 YYYY-MM-DD（默认今天）")
    s.add_argument("--niche", default="finance", help="赛道目录（默认 finance）")
    s.add_argument("--out", default="", help="可选：覆盖输出目录（不走 episodes）")
    s.add_argument("--zip", default="", help="可选：覆盖 zip 路径")
    s.add_argument("--no-zip", action="store_true", help="只生成目录，不打 zip")
    s.add_argument("--single", action="store_true", help="单文件 HTML（仅 douyin/bilibili）")
    s.add_argument("--force", action="store_true", help="校验失败仍打包")
    s.set_defaults(func=cmd_generate)

    s = sub.add_parser("pack", help="校验并打 zip")
    s.add_argument("path", help="源目录")
    s.add_argument("--zip", required=True, help="输出 zip 路径")
    s.add_argument("--force", action="store_true")
    s.set_defaults(func=cmd_pack)

    args = p.parse_args(argv)
    return int(args.func(args) or 0)


if __name__ == "__main__":
    raise SystemExit(main())
