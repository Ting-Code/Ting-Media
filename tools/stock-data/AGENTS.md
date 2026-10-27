# AGENTS.md — tools/stock-data

公共 **公开市场取数工具**。需要行情/财务指标/指标序列时调用本目录，不要手写假数据。

```bash
cd tools/stock-data
pip install -r requirements.txt
```

在其它工具中把 `tools/stock-data/src` 加入 `sys.path` 后 import（见 `docs/数据源规范.md`）。

录屏 HTML 请用 `tools/stock-analysis`（会调用本工具）。

## 合规

生成数据仅供参考；不授权商用；请勿滥用。
