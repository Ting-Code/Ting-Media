# AGENTS.md — tools/stock-screener

大 A 选股和估值。原始数据只从 `tools/stock-data` 来。不生成录屏 HTML。

先看用户要哪一件，只走对应入口。

## 要什么，调哪个

| 要什么 | 入口 |
|---|---|
| 一只股票的 PE、PB、股息率、分位 | `python scripts/analyze_symbol.py <名称或代码>` |
| 全 A 股息率 | `python scripts/div_yield.py` |
| 全市场按一套形态筛选 | `python scripts/run_screener.py --config configs/<配置>.yaml` |

单股脚本只打印结果。全 A 股息率写到仓库根 `cache/div_yield_<行情日>/`。筛选结果写到 `cache/<配置名>_<日期>/`。

估值取数：成交价 `fetch_daily(..., adjust="bfq")`。股息率分子是东财定期报告期已实施现金 `fetch_dividends`，最近四个已结束报告期合计，不含特别分红。PE / PB 口径见 `docs/分析口径.md`。

## 筛选配置

日线规则位先空着：`configs/` 放筛选配置，`src/filters/pattern.py` 放形态。等另一台电脑上已写好的规则合并后再跑 `run_screener.py`。现在不要自己补规则。

## 合规

生成名单与指标仅供参考；不构成投资建议。
