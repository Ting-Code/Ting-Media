# AGENTS.md — Ting-Media

自媒体录屏工作台。目录约定见 `docs/目录规划.md`。

## 工具

| 工具 | 用途 | 规范 |
|------|------|------|
| `tools/stock-data` | A 股取数 / 估值序列 | `tools/stock-data/docs/数据源规范.md` |
| `tools/stock-analysis` | 9:16 PPT 录屏页 | `tools/stock-analysis/docs/9-16-录屏规范.md` |

```bash
cd tools/stock-analysis
pip install -r requirements.txt
pip install -r ../stock-data/requirements.txt
python scripts/generate_stock_html.py <名称或代码> [--theme 主题] [--date YYYY-MM-DD]
```

产物：`episodes/<niche>/YYYY-MM-DD_主题/index.html`  
禁止从零手写整页 HTML。财经科普/复盘，不荐股；相关工具不授权商用。
