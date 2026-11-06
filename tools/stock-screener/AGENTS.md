# AGENTS.md — tools/stock-screener

大 A **选股 + 基本面/估值分析**。原始行情与财报取自 `tools/stock-data`（勿再维护本地 tdx 解析）。

## 能力

| 模块 | 用途 |
|------|------|
| `pipeline` + `filters/` | 技术面全市场筛选 |
| `analysis` | 单季/TTM 面板、PE/PB、分位 |
| `docs/分析口径.md` | PE/PB 与出图口径 |

## 用法

```bash
cd tools/stock-screener
pip install -r ../stock-data/requirements.txt
pip install -r requirements.txt
python scripts/run_screener.py --config configs/v1_tech.yaml
# -> cache/screener_v1_tech_YYYY-MM-DD/
```

## 合规

生成名单与指标仅供参考；不构成投资建议。
