# AGENTS.md — tools/stock-analysis

录屏用 **9:16 PPT 数据页** 生成器。取数请用 `tools/stock-data`（本工具会调用它）。

```bash
cd tools/stock-analysis
pip install -r requirements.txt
pip install -r ../stock-data/requirements.txt
python scripts/generate_stock_html.py <名称或代码> [--theme 主题] [--date YYYY-MM-DD] [--niche finance]
```

| 本工具 | `tools/stock-data` |
|--------|-------------------|
| PPT 母版、安全区、切页、Plotly 出页 | 行情 / 财务指标 / 指标序列 |

生成数据仅供参考；不授权商用；请勿滥用。细则见 `docs/`。
