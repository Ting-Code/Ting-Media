# AGENTS.md — tools/stock-analysis

录屏用 **9:16 PPT 复盘页** 生成器。取数请用 `tools/stock-data`（本工具会调用它）。

## 生成

```bash
cd tools/stock-analysis
pip install -r requirements.txt
pip install -r ../stock-data/requirements.txt
python scripts/generate_stock_html.py <名称或代码> [--theme 主题] [--date YYYY-MM-DD] [--niche finance]
```

产物：`episodes/<niche>/YYYY-MM-DD_主题/index.html`

## 职责

| 本工具 | `tools/stock-data` |
|--------|---------------------|
| PPT 母版、安全区、切页、Plotly 出页 | 行情/季报/分红/估值序列 |
| `docs/方案.md`（分析块与出页） | `docs/数据源规范.md` |

禁止从零手写整页 HTML。规范见`docs/9-16-录屏规范.md`（本工具）。
