# AGENTS.md — Ting-Media

自媒体录屏工作台。先读本文件；细则链到 `docs/` 与具体工具目录。

## 三块目录

- `docs/`：公共规范  
- `episodes/<赛道>/YYYY-MM-DD_主题/`：每期录屏内容  
- `tools/<工具名>/`：公共工具（**不按赛道分**，用到再调用）

见 `docs/目录规划.md`。

## 录屏硬规则

- **9:16** PPT 一屏一页；空格/方向键切页  
- 核心内容避开平台上下遮挡（`docs/9-16-录屏规范.md`）  
- **禁止**从零手写整页 HTML；母版固定，只变内容/数据（`docs/录屏产物与生成方式.md`）

## 调用股票复盘工具

```bash
cd tools/stock-analysis
pip install -r requirements.txt
python scripts/generate_stock_html.py <名称或代码> [--theme 主题] [--date YYYY-MM-DD] [--niche finance]
```

产物：`episodes/<niche>/YYYY-MM-DD_主题/index.html`  
工具说明：`tools/stock-analysis/AGENTS.md`  
合规：科普/复盘，不荐股；该工具不授权商用。
