# AGENTS.md — tools/stock-data

公共 **A 股取数工具**。需要行情/季报/估值序列时调用本目录，不要手写假数据。

## 用法

```bash
cd tools/stock-data
pip install -r requirements.txt
```

在其它工具中把 `tools/stock-data/src` 加入 `sys.path` 后 import（见 `docs/数据源规范.md`）。

录屏 HTML 请用 `tools/stock-analysis`（会调用本工具）。

## 规范

- 数据源与口径：`docs/数据源规范.md`
- 不荐股；数据仅供复盘学习
