# interactive-pack

按抖音互动空间 / B站 Toy / 小红书小工具规范，生成离线互动 HTML（不是 9:16 录屏页）。

## 输出约定（一期一个文件夹）

```text
episodes/<赛道>/YYYY-MM-DD_主题/
  index.html              # 录屏页（screen-pack / platform-trends --html）
  meta.json
  interactive/            # 本工具：互动包源文件
  interactive-common.zip  # 本工具：可上传 zip
```

互动放在子目录 `interactive/`，避免覆盖录屏 `index.html`。

## 命令

```bash
cd tools/interactive-pack

python scripts/cli.py --platform common generate \n  --content examples/sample.json \n  --theme 今日热度速览 \n  --date 2026-11-05 \n  --niche finance
```

本地调试可用 `--out ../../cache/debug-interactive`；正式节目用 `--theme/--date/--niche` 写入 episodes。

## 内容 JSON

见 `examples/sample.json`。规范见 `docs/平台规范.md`。
