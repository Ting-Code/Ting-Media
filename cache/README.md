# cache

分析/选股过程的临时结果放这里，**按分析名分子目录**，不要写到 `tools/*/output/`。

```text
cache/
  screener_v1_tech_YYYY-MM-DD/
  2026-11-05_宁德时代复盘/
  README.md
```

- 成片 HTML / 互动包 → `episodes/<赛道>/YYYY-MM-DD_主题/`
- **金融原始数据**（东财季报、gbbq 解密等）→ `tools/stock-data/cache/`（不在本目录）
- 目录可删可再生；除本 README 外不入库
