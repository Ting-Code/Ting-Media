# stock-analysis（Ting-Media 子模块）

> 归属：[Ting-Media](https://github.com/Ting-Code/Ting-Media) → `tools/stock-analysis/`

输入标的名称或代码 → 生成可交互的 9:16 浏览器页（行情 / 财务指标 / 指标序列），供个人学习与录屏参考。

| 块 | 内容 |
|----|------|
| **A** | 行情 K 线（前复权；日/周/月/季） |
| **B** | 季度财务指标 |
| **C** | 指标序列（锚定次月月末收盘；TTM 扣非市盈 + 市净 + 股息率） |

```bash
cd tools/stock-analysis
pip install -r requirements.txt
pip install -r ../stock-data/requirements.txt
python scripts/generate_stock_html.py <名称或代码>
# -> episodes/<赛道>/YYYY-MM-DD_主题/index.html
```

取数依赖 `tools/stock-data`。生成数据仅供参考，不构成决策依据；不授权商用；请勿滥用。
