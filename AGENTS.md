# AGENTS.md — Ting-Media

内容工作台：工具取数/出图 → 竖屏录屏 HTML → 按期归档。

## 目录

```text
Ting-Media/
├── AGENTS.md
├── episodes/<赛道>/YYYY-MM-DD_主题/
└── tools/
    ├── stock-data/
    └── stock-analysis/   # 录屏 HTML；视觉规范已定稿
```

## 两条工作流

### 1）数据分析（先查能力，勿乱加工具）

1. 先看现有工具能否覆盖（`stock-data` / `stock-analysis`）。
2. **有能力就直接调用**。
3. **同一类需求反复出现**再封装；不要一提新需求就新建工具。

### 2）生成一期节目

1. 跑 `tools/stock-analysis` 流水线（内部用 `stock-data`）。
2. 写入 `episodes/<赛道>/YYYY-MM-DD_主题/index.html`。
3. **禁止**手写整页 HTML。布局 / 大小 / 主题以  
   `tools/stock-analysis/docs/9-16-录屏规范.md` 与母版为准——**换期只换内容**。

```bash
cd tools/stock-analysis
pip install -r requirements.txt
pip install -r ../stock-data/requirements.txt
python scripts/generate_stock_html.py <名称或代码> [--theme 主题] [--date YYYY-MM-DD] [--niche finance]
```

## 已定稿规范（勿擅自改画法）

- 录屏视觉：`tools/stock-analysis/docs/9-16-录屏规范.md` + deck 母版
- 估值取数与 **PE 分析图**：`tools/stock-data/docs/数据源规范.md`  
  单股/板块同一套：PE、PB、股价（或点位）**各用独立纵轴**，刻度可隐藏、悬浮看真值；禁止共用绝对刻度、禁止末点=100 归一

## 合规

生成数据仅供参考，不构成决策依据；不授权商用；请勿滥用。
