# AGENTS.md — tools/screen-pack

录屏 HTML 生成器。取数：`tools/stock-data`；估值/基本面面板：`tools/stock-screener`。

- **视觉契约**：[`docs/9-16-录屏规范.md`](docs/9-16-录屏规范.md)（实现：`src/_deck_template.html` / `_deck_nav.js` / `render_report.py`）
- **换期只换内容**，不改母版版式

```bash
cd tools/screen-pack
pip install -r requirements.txt
pip install -r ../stock-data/requirements.txt
python scripts/generate_stock_html.py <名称或代码> [--theme 主题] [--date YYYY-MM-DD] [--niche finance]
```

生成数据仅供参考；不授权商用。

分析 CSV 写入仓库根 `cache/<YYYY-MM-DD_主题>/`，成片在 `episodes/`。

主入口：`scripts/generate_stock_html.py`。`generate_sector_*.py` 为板块专题一次性脚本，按需用。
