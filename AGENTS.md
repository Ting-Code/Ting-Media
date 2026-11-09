# AGENTS.md — Ting-Media

内容工作台。五个工具彼此独立；只有用户明确要做节目时，才用 `screen-pack` 出竖屏 HTML。

## 目录

```text
Ting-Media/
├── AGENTS.md
├── episodes/<赛道>/YYYY-MM-DD_主题/
└── tools/
    ├── stock-data/       # 取数；行情直读通达信，仅财报缓存（工具内）
    ├── screen-pack/    # 录屏 HTML；视觉规范已定稿
    ├── stock-screener/    # 选股 + 基本面/估值分析
    ├── platform-trends/   # 跨平台热榜；免 Key 三家
    └── interactive-pack/  # 抖音/B站Toy/小红书 离线互动 HTML
```

## 一期节目归档

同一期的**所有产物**放进同一个目录：

```text
episodes/<赛道>/YYYY-MM-DD_主题/     # 成片
  index.html
  meta.json                    # 含 "cache": "cache/…"
  interactive/ …               # 互动包（如有）

cache/<分析名>/                  # 分析/选股结果（仓库根）；财报原始缓存见 stock-data/cache
  …csv / …json
```

分析名通常与期次文件夹同名（`YYYY-MM-DD_主题`）；未立题探数用如 `trends_2026-11-05`。  
不要写到 `tools/*/output/` 或仓库根 `output/`。

## 工具各自独立

`stock-data`、`stock-screener`、`platform-trends`、`screen-pack`、`interactive-pack` 分开调用。分析、选股、热度默认只给数据。没必要不要调用 `screen-pack` 出 HTML；只有用户明确说「录屏 / 出一期 / 做节目」时才生成。

## 工作流

### 1）数据分析（先查能力，勿乱加工具）

1. 先看取数和分析工具能否覆盖（`stock-data`、`stock-screener`、`platform-trends`）。
2. **有能力就直接调用**。不要为了出图去调用 `screen-pack`。
3. **同一类需求反复出现**再封装；不要一提新需求就新建工具。
4. 只有用户明确要求成片时，才进入下面的节目流程。

### 2）生成一期节目

1. 跑 `tools/screen-pack` 流水线（取数 `stock-data`，分析 `stock-screener`）。
2. 写入 `episodes/<赛道>/YYYY-MM-DD_主题/index.html`。
3. **禁止**手写整页 HTML。布局 / 大小 / 主题以  
   `tools/screen-pack/docs/9-16-录屏规范.md` 与母版为准——**换期只换内容**。

```bash
cd tools/screen-pack
pip install -r requirements.txt
pip install -r ../stock-data/requirements.txt
python scripts/generate_stock_html.py <名称或代码> [--theme 主题] [--date YYYY-MM-DD] [--niche finance]
```


### 3）跨平台热度（平台上什么在火）

免 Key 拉 B站热门作品、微博热搜、抖音热词；汇总赛道与话题。小红书 / 视频号未接入。规范见 `tools/platform-trends/docs/数据源规范.md`。

**默认只给数据摘要**。未明确说要录屏节目时，不要出 HTML；需要录屏时再加 `--html`。

```bash
cd tools/platform-trends
pip install -r requirements.txt
python scripts/analyze_trends.py
# 录屏节目才加：--html --theme 今日热度
```


### 4）选股与估值分析

技术面筛选 + 基本面面板/PE。取数只走 `stock-data` 的能力表（`tools/stock-data/AGENTS.md`）。分析只走 `tools/stock-screener/AGENTS.md`：单股用 `scripts/analyze_symbol.py`，全 A 股息率用 `scripts/div_yield.py`，全市场筛选用 `scripts/run_screener.py --config`。不调用 `screen-pack`。

```bash
cd tools/stock-screener
pip install -r ../stock-data/requirements.txt
pip install -r requirements.txt
python scripts/analyze_symbol.py <名称或代码>
python scripts/div_yield.py
# 日线筛选配置位先空着，规则合并后再：
# python scripts/run_screener.py --config configs/<配置>.yaml
```


### 5）互动 HTML（抖音互动空间 / B站 Toy / 小红书小工具）

按平台离线包规范生成可上传 zip，**不是** 9:16 录屏页；写入**同一期** episodes 目录。规范见 `tools/interactive-pack/docs/平台规范.md`。

```bash
cd tools/interactive-pack
python scripts/cli.py --platform common generate \n  --content examples/sample.json \n  --theme 今日热度速览 \n  --date 2026-11-05 \n  --niche finance
# -> episodes/finance/2026-11-05_今日热度速览/interactive/ + interactive-common.zip
```

默认 `common` 可过三端校验；仅抖音/B站单文件时加 `--single --platform douyin|bilibili`。

## 已定稿规范（勿擅自改画法）

- 录屏视觉：`tools/screen-pack/docs/9-16-录屏规范.md` + deck 母版  
  单股/板块同一套：PE、PB、股价（或点位）**各用独立纵轴**，刻度可隐藏、悬浮看真值；禁止共用绝对刻度、禁止末点=100 归一
- 互动离线包：`tools/interactive-pack/docs/平台规范.md`（与录屏母版分开）
- 取数：`tools/stock-data/`（缓存内化 `tools/stock-data/cache/`）
- PE/基本面分析口径：`tools/stock-screener/docs/分析口径.md`

## 合规

生成数据仅供参考，不构成决策依据；不授权商用；请勿滥用。
