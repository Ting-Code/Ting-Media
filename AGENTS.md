# AGENTS.md — Ting-Media

自媒体录屏工作台。先读本文件；细则链到 `docs/` 与 `tools/<工具名>/`。

## 三块目录

- `docs/`：公共规范  
- `episodes/<赛道>/YYYY-MM-DD_主题/`：每期录屏内容  
- `tools/<工具名>/`：公共工具（不按赛道分，用到再调）

见 `docs/目录规划.md`。

## 录屏硬规则

- **9:16** PPT 一屏一页；空格/方向键切页  
- 避开平台上下遮挡（`docs/9-16-录屏规范.md`）  
- **禁止**从零手写整页 HTML（`docs/录屏产物与生成方式.md`）

## 常用工具

| 工具 | 用途 |
|------|------|
| `tools/stock-data` | A 股取数 + 估值序列（规范：`docs/数据源规范.md`） |
| `tools/stock-analysis` | 套 PPT 母版生成录屏 HTML（会调用 stock-data） |

```bash
cd tools/stock-analysis
pip install -r requirements.txt
pip install -r ../stock-data/requirements.txt
python scripts/generate_stock_html.py <名称或代码> [--theme 主题] [--date YYYY-MM-DD]
```

产物：`episodes/<niche>/YYYY-MM-DD_主题/index.html`  
合规：科普/复盘，不荐股；股票相关工具不授权商用。
