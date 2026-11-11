# AGENTS.md — tools/stock-data

公共取数。不做 PE、选股、分位，那些在 `tools/stock-screener`。

把 `tools/stock-data/src` 加入 `sys.path` 后，只从 `market`、`fundamentals`、`codes`、`holdings` 导入。`tdx_day`、`tdx_xdxr`、`adjust`、`store` 是内部实现。

指数不要用 `fetch_daily("000300")`，6 位代码会按股票去找文件。指数用 `fetch_index_daily("sh000300")` 或 `fetch_index_daily("sz399006")`。

## 要什么，调哪个

| 要什么 | 只调 |
|---|---|
| 成交价（估值、股息率分母） | `fetch_daily(code, adjust="bfq")` |
| 全 A 最新不复权收盘 | `fetch_a_share_last_close()` |
| 指数日线（不复权，带市场代码） | `fetch_index_daily("sh000300")` |
| 分板块按日成交额合计 | `fetch_boards_daily_amount()` |
| ETF 份额、板块总市值 | `holdings.fetch_sse_etf_shares` / `fetch_szse_etf_shares` / `fetch_board_caps` |
| 证券简称 | `load_security_names()` |
| 复权走势 | `fetch_daily(code)`（默认前复权）或 `adjust="hfq"` |
| 周 / 月 / 季线 | `resample_ohlcv`，周期 `W`、`M` 或 `Q` |
| 单只已除息现金分红（含特别分红，用于复权） | `fetch_cash_dividends(code)` |
| 全 A 已除息现金分红（含特别分红，用于复权） | `fetch_a_share_cash_dividends()` |
| 单只定期报告期现金分红（股息率分子，不含特别分红） | `fetch_dividends(code)` |
| 某一个报告期的全市场现金分红 | `fetch_period_cash_dividends(report_date)` |
| 季报利润表 | `fetch_quarterly_profit(code)` |
| 季报资产负债表 | `fetch_quarterly_balance(code)` |
| 代码或名称 | `resolve_code(query)` |

股息率分子用 `fetch_dividends` 或 `fetch_period_cash_dividends`：东财定期报告期里已实施、已除息的现金，不含特别分红。取最近四个已结束报告期加总。分母用 `adjust="bfq"` 的收盘价。`fetch_cash_dividends` 来自通达信 gbbq，含特别分红，用于复权。

## 来源

- 行情、复权用的已除息现金：本机通达信 `vipdoc` 日线 + `gbbq`。日线不落盘。`gbbq.parquet` 只加速解密。
- 季报、定期报告期现金分红：东财。缓存 `tools/stock-data/cache/`（`em_profit` / `em_balance` / `em_dividend`）。
- 环境变量（可选）：`TDX_DIR` / `TDX_VIPDOC` / `TDX_GBBQ` / `STOCK_DATA_CACHE`

## 东财财报缓存（硬规则）

- 利润表 / 资产负债表 / 定期报告期分红：每次拉到后写入 `cache/` 对应 parquet（按股一份全字段）。
- **有缓存先读缓存**；不按 24 小时或其它时间自动过期，不重复请求东财。
- 以后要收入、同比、费用、EPS 等字段，先看本地缓存列，不要再调接口。
- 只有调用方显式 `refresh=True` 才重新请求并覆盖缓存。

录屏只有用户明确要求做节目时才走 `tools/screen-pack`。

## 合规

生成数据仅供参考；不授权商用；请勿滥用。

## 港股

- 代码：`00700` / `00700.HK` / 名称（如腾讯控股）。`resolve_code` 返回 `00700.HK`，不要把 5 位代码补成 6 位 A 股。
- 日线：`fetch_daily(code, adjust="bfq")`。本机通达信 `vipdoc/ds/lday/31#00700.day`，浮点价格，不复权。港股未收盘前会去掉当天可能未完成的一根。
- 财报：`fetch_quarterly_profit` / `fetch_quarterly_balance` 自动走东财港股报告期（`em_hk_profit` / `em_hk_balance`），有缓存先读。盈利用股东应占溢利，不是 A 股扣非。
- 汇率：`fetch_fx_hkdcnyc()`，港币人民币中间价，缓存 `em_fx/HKDCNYC.parquet`。
- 港股暂不提供 A 股那套东财分红表，`fetch_dividends` 返回空表。
