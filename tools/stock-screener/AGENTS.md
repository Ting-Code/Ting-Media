# AGENTS.md — tools/stock-screener

大 A 选股和估值。原始数据只从 `tools/stock-data` 来。不生成录屏 HTML。

先看用户要哪一件，只走对应入口。

## 要什么，调哪个

| 要什么 | 入口 |
|---|---|
| 一只或一组股票的 PE、PB、分位，以及横版分析页 | `python scripts/analyze_symbol.py <名称或代码>`；多只时加 `--title` |
| 全 A 股息率 | `python scripts/div_yield.py` |
| 头部 ETF 持有规模占板块总市值 | `python scripts/etf_market_share.py` |
| 全市场按一套形态筛选 | `python scripts/run_screener.py --config configs/<配置>.yaml` |
| 全 A 历史 PE、PB 都低分位 | `python scripts/screen_low_valuation.py` |

单股脚本打印结果，并把同一张 PE/PB/股价图写成普通横版网页 `cache/pe_<代码>_<行情日>/index.html`（主图 + 下方色带选区间；不要区间按钮，也不要平移/框选）。一次传入多只股票时，只写一张总览页 `cache/pe_<主题>_<行情日>/index.html`，不再写各自的单股页：页顶对照表，下面每只一块同样的主图和色带，右侧固定导航点击滚动到对应图表。这不是录屏 HTML。全 A 股息率写到仓库根 `cache/div_yield_<行情日>/`。头部 ETF 持有规模占比写到 `cache/etf_market_share_<行情日>/index.html`。筛选结果写到 `cache/<配置名>_<日期>/`。全 A 历史 PE、PB 低分位走 `scripts/screen_low_valuation.py`：先按报告期全量拉取东财主要指标（含扣非、每股净资产、总股本）并缓存，再按官方口径在本地算分位；默认双分位均 ≤20% 且有效点均 ≥12，结果写 `cache/pe_pb_low_<行情日>/`（总览 HTML + CSV，含上市板和通达信一/二/三级行业），不为每只出图。

港股同样走这个入口：`python scripts/analyze_symbol.py 00700`（也可用 `00700.HK` 或名称）。写出 `cache/pe_00700_<行情日>/index.html`，导语按港股口径，版式不变。多只港股或与 A 股混合时，总览页目录名用 `--title`，例如 `python scripts/analyze_symbol.py --title 513330_top10 00700 09988`。

估值取数：成交价 `fetch_daily(..., adjust="bfq")`。港股为通达信不复权港元收盘，PE/PB 按港币人民币中间价折算；盈利用股东应占溢利，不用 A 股扣非。股息率分子是东财定期报告期已实施现金 `fetch_dividends`，最近四个已结束报告期合计，不含特别分红。PE / PB 口径见 `docs/分析口径.md`。

## 筛选配置

日线规则位先空着：`configs/` 放筛选配置，`src/filters/pattern.py` 放形态。等另一台电脑上已写好的规则合并后再跑 `run_screener.py`。现在不要自己补规则。

## 合规

生成名单与指标仅供参考；不构成投资建议。
