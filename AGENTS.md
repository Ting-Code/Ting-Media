# AGENTS.md — Ting-Media

自媒体录屏工作台。AI 只读本文件 + 链到的 docs/工具说明，**不要**从零发明页面结构。

## 目录（记住三个）

- `docs/`：公共规范  
- `episodes/<赛道>/YYYY-MM-DD_主题/`：每期录屏内容  
- `tools/...`：可运行工具（规范在工具目录内）

详见 `docs/目录规划.md`。

## 录屏硬规则

- 画幅 **9:16**；**PPT 一屏一页**；空格/方向键切页平滑滚动  
- 核心内容避开抖音/B站上下遮挡区（见 `docs/9-16-录屏规范.md`）  
- **禁止**每次手写整页 HTML；母版固定，只变内容/数据（见 `docs/录屏产物与生成方式.md`）

## 财经复盘（真数）

```bash
cd tools/finance/stock-analysis
pip install -r requirements.txt
python scripts/generate_stock_html.py <名称或代码> [--theme 主题] [--date YYYY-MM-DD]
```

产物：`episodes/finance/YYYY-MM-DD_主题/index.html`  
工具细则：`tools/finance/stock-analysis/AGENTS.md`  
合规：科普/复盘，不荐股、不承诺收益；该工具不授权商用。
