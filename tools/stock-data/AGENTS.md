# AGENTS.md — tools/stock-data

公共 **取数 + 财报缓存**。不要在本工具做 PE/选股/面板分析（那些在 `tools/stock-screener`）。

```bash
cd tools/stock-data
pip install -r requirements.txt
```

把 `tools/stock-data/src` 加入 `sys.path` 后 import（见 `docs/数据源规范.md`）。

## 原则

- **行情（通达信）**：直接读本机 `vipdoc` lday + `gbbq` 现场复权/重采样（`src/market.py`）。**不落盘缓存 K 线**（日/周/月均现算）。
- **财报（东财）**：利润表 / 资产负债表等才写入 **`tools/stock-data/cache/`**（`em_profit` / `em_balance`）。
- `cache/tdx/gbbq.parquet` 仅作权息文件解密加速（可选），不是行情副本；分析仍以通达信源文件为准。
- 环境变量（可选）：`TDX_DIR` / `TDX_VIPDOC` / `TDX_GBBQ` / `STOCK_DATA_CACHE`

录屏 HTML：`tools/screen-pack`（分析口径走 screener）。

## 合规

生成数据仅供参考；不授权商用；请勿滥用。
