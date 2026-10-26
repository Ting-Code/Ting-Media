## 所在位置

本模块位于 `Ting-Media/tools/finance/stock-analysis/`。请在该目录下安装依赖并运行生成脚本。

# AGENTS.md — 给 AI / 协作者的项目说明书

你在协助维护 **Ting-Stock-Analysis**：A 股**单票**复盘 HTML 生成器。  
用户说出股票名称或代码时，目标是生成与现有母版结构一致的交互式 HTML，而不是从零重写一页网页。

## 先读这些

1. `docs/方案.md` — 产品方向与已确认分析口径  
2. `README.md` — 安装与命令  
3. 本文件 — 生成时必须遵守的流程  

## 用户一句话时你该做什么

当用户说类似「帮我生成贵州茅台 / 600519 的复盘页」：

1. **不要**手写一整页无数据的假 HTML。  
2. **优先**复用现有流水线：

```bash
pip install -r requirements.txt
python scripts/generate_stock_html.py <名称或6位代码>
```

3. 产物路径：`output/<代码>_<名称>_复盘.html`（`output/` 不入库）。  
4. 若名称不在 `src/codes.py` 的 `NAME_TO_CODE` 中：用 **6 位代码** 调用脚本；需要时可把常用名称补进映射。  
5. 生成后用浏览器打开检查：A K线 / B 季报 / C 估值 三块是否齐全，并提醒免责声明口径。

## 架构约定（勿破坏）

| 层 | 职责 | 主要文件 |
|----|------|----------|
| 取行情 | BaoStock 前复权日线，重采样日/周/月/季 | `src/market.py` |
| 取财报 | 东财季报（经 AkShare），累计拆单季；分红 | `src/fundamentals.py` |
| 估值 | 发布日次月**月末收盘**锚定；TTM 扣非 PE、PB、股息率 | `src/valuation.py` |
| 渲染 | HTML 母版 + Plotly 交互图 | `src/render_report.py` |
| 入口 | CLI | `scripts/generate_stock_html.py` |

HTML 只是**展示壳**，默认按 **9:16 竖屏**排版（短视频截图友好）。数据、计算、（未来）文案解读应保持模块分离；禁止把整套逻辑糊进单文件静态页后丢弃管线。

## 已锁定口径（改之前先问用户）

- 复权：前复权  
- 锚定价：季报 NOTICE 的**次月**最后一个交易日收盘价  
- PE：每股 TTM 扣非（近 4 个单季扣非之和）  
- 第一版：**只做单票**；板块第二版  
- 合规：科普/复盘，不荐股、不承诺收益，页面保留免责声明  

## 改代码时

- 扩展图表：优先改 `src/render_report.py` 母版与积木，而不是让模型每篇新写 HTML。  
- 新股票名称：更新 `src/codes.py` 的 `NAME_TO_CODE`。  
- `app.py` 是早期 Streamlit 试做，正式产物以 `scripts/generate_stock_html.py` → HTML 为准。  
- 不要提交 `output/`。  

## 推荐提示词（人类可复制给 AI）

```text
请阅读 AGENTS.md 与 docs/方案.md，用本仓库现有流水线为「股票名或代码」生成复盘 HTML，
不要从零手写页面。生成后告诉我 output 路径，并简述 PE/PB/股息率与口径。
```

## 排错与名称解析

- 详细协作说明：`docs/AI协作指南.md`
- 名称解析：`src/codes.py`（别名 → 6 位代码 → AkShare 简称表）
- 网络失败时让用户重试或改用代码，不要伪造数据凑 HTML

