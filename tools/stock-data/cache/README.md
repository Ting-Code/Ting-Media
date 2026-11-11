# stock-data 财报缓存（工具内化）

**只缓存财报原始数据**，不入库（见根 `.gitignore`）。

有文件就读，不按时间自动过期；只有 `refresh=True` 才重新拉东财覆盖。

| 路径 | 内容 |
|------|------|
| `em_profit/by_code/` | 东财利润表全字段（按股） |
| `em_profit/by_quarter/{YYYYMMDD}/` | 同报告期截面 |
| `em_balance/by_code/` | 东财资产负债表全字段 |
| `em_dividend/by_code/` | 东财分红（已实施） |
| `em_hk_profit/by_code/` | 东财港股利润表（按股，已转宽表） |
| `em_hk_balance/by_code/` | 东财港股资产负债表（按股） |
| `em_fx/` | 汇率（如 HKDCNYC 港币人民币中间价） |
| `tdx/gbbq.parquet` | （可选）权息解密加速，非 K 线 |

通达信日线/周月线：**不在此存储**，分析时直读本机 `vipdoc`。

选股/分析结果仍写仓库根 `cache/<分析名>/`。
