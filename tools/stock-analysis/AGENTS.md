# AGENTS.md — tools/stock-analysis

录屏 HTML 生成器。取数：`tools/stock-data`。

- **视觉契约**：[`docs/9-16-录屏规范.md`](docs/9-16-录屏规范.md)（实现：`src/_deck_template.html` / `_deck_nav.js` / `render_report.py`）
- **换期只换内容**，不改母版版式

```bash
cd tools/stock-analysis
pip install -r requirements.txt
pip install -r ../stock-data/requirements.txt
python scripts/generate_stock_html.py <名称或代码> [--theme 主题] [--date YYYY-MM-DD] [--niche finance]
```

生成数据仅供参考；不授权商用。
