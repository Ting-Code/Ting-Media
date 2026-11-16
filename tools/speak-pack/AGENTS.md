# AGENTS.md — tools/speak-pack

口播 / 跟读 9:16 录屏 HTML 生成器。与 `screen-pack` 相互独立，不改股票录屏母版。

- **视觉契约**：[`docs/9-16-口播录屏规范.md`](docs/9-16-口播录屏规范.md)（实现：`src/_speak_template.html` / `_speak_nav.js`）
- **换期只换内容**，不改母版版式
- 只有用户明确要做口播 / 跟读节目时才生成

```bash
cd tools/speak-pack
python scripts/generate_speak_html.py examples/sample.json [--theme 跟读名言] [--date YYYY-MM-DD] [--niche english]
python scripts/serve_episode.py ../../episodes/english/2026-11-16_跟读名言
```

成片写入 `episodes/<niche>/YYYY-MM-DD_主题/index.html`。
