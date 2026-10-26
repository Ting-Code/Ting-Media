# AGENTS.md — Ting-Media

本仓库是自媒体（短视频 / 图文）工作台总项目。默认展示与录屏按 **9:16 竖屏 PPT 分镜**（切页滚动；内容避开平台上下遮挡区）。见 `shared/workflow/9-16-录屏规范.md`。

目录规划详见 [`docs/目录规划.md`](docs/目录规划.md)。

## 怎么找东西

| 你要… | 去哪 |
|--------|------|
| 跨赛道流程 / 通用模板 | `shared/` |
| 财经或生活的口播、提示词、检查表 | `niches/finance` 或 `niches/life` |
| 可运行脚本 | `tools/` |
| A 股复盘 HTML | `tools/finance/stock-analysis/` |
| 每期录屏产物 | `episodes/<赛道>/日期_主题/` |

## 股票复盘

1. 读 `tools/finance/stock-analysis/AGENTS.md`
2. `cd tools/finance/stock-analysis && pip install -r requirements.txt`
3. `python scripts/generate_stock_html.py <名称或代码> [--theme 主题] [--date YYYY-MM-DD]`
4. 产物：`episodes/finance/YYYY-MM-DD_主题/index.html`（见 docs/录屏产物与生成方式.md）
5. 不要从零手写整页 HTML；母版固定，只变内容/数据

## 原则

- 赛道只沉淀内容资产；工具按用途放 `tools/`，不按赛道复制整套代码
- 财经：科普 / 复盘，不荐股、不承诺收益
- `tools/finance/stock-analysis` 不授权商用
