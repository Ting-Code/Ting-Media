# Stock Analysis（Ting-Media 子模块）

> 归属仓库：[Ting-Media](https://github.com/Ting-Code/Ting-Media) → `tools/finance/stock-analysis/`  
> 原独立仓库 `Ting-Stock-Analysis` 已归并至此。


> 输入一只 A 股 → 生成可交互的浏览器复盘页  
> 给个人学习与自媒体内容生产用，不做荐股、不授权商用。

把行情、季报、估值收成一页 HTML：能缩放看 K 线，也能对照盈利与估值分位，方便复盘和写稿。

---

## 一次生成，三块内容

| | 模块 | 你看到什么 |
|---|------|------------|
| **A** | 行情 K 线 | 前复权；日 / 周 / 月 / 季切换；缩放、拖动 |
| **B** | 季度财报 | 营收、归母净利、扣非（累计报表已拆成单季） |
| **C** | 估值序列 | 季报发布日**次月月末收盘**为锚；TTM 扣非 PE + PB + 股息率，对比现价分位 |

产出是独立 HTML，**默认按 9:16 竖屏**排版（短视频截图友好）；宽屏也保持竖栏，不拉成横版仪表盘。  
第一版只做**单票**，板块放到后面。

---

## 快速开始

**环境：** Python 3.10+，并能访问 BaoStock、东方财富相关接口（经 AkShare）。

```bash
pip install -r requirements.txt
python scripts/generate_stock_html.py 宁德时代
# 或：python scripts/generate_stock_html.py 300750
```

生成文件在 `output/`（已忽略进库）。用浏览器打开即可。

<details>
<summary>可选：早期 Streamlit 试做</summary>

```bash
streamlit run app.py
```

正式产物以 HTML 流水线为准。
</details>

---

## 项目结构

```text
Ting-Stock-Analysis/
├── AGENTS.md                 # 给 AI 的操作说明书
├── docs/
│   ├── 方案.md               # 产品方向与分析口径
│   └── AI协作指南.md         # 提示词、验收与排错
├── scripts/
│   └── generate_stock_html.py
├── src/
│   ├── market.py             # 日线与周期重采样
│   ├── fundamentals.py       # 季报 / 分红
│   ├── valuation.py          # PE / PB / 股息率
│   └── render_report.py      # HTML 母版渲染
├── output/                   # 本地生成物（不入库）
└── requirements.txt
```

---

## 分析口径

| 项目 | 口径 |
|------|------|
| 复权 | 前复权 |
| 估值锚定价 | 季报 `NOTICE` 所在月的**下一个自然月**，取该月**最后一个交易日收盘价** |
| 动态 PE | 锚定日价格 ÷ 每股 **TTM 扣非**（近 4 个单季扣非之和） |
| 股息率 | 近 12 个月已实施现金分红 ÷ 价格 |
| 范围 | 第一版仅单票 |

完整方案见 [`docs/方案.md`](docs/方案.md)。

**数据：** 行情来自 [BaoStock](http://baostock.com/)；财报与分红来自东方财富（经 [AkShare](https://github.com/akfamily/akshare)）。接口可能变动，重要结论请与交易所 / 巨潮交叉核对。

---

## 给协作者 / AI

克隆后，用 Cursor 等能读仓库的 AI，可按同一流水线出页：

1. 确保能读到根目录 [`AGENTS.md`](AGENTS.md)（以及 `.cursor/rules/`）
2. `pip install -r requirements.txt`
3. 对 AI 说（可直接复制）：

```text
请阅读 AGENTS.md 与 docs/方案.md，用本仓库现有流水线为「宁德时代」生成复盘 HTML，
不要从零手写页面。生成后告诉我 output 路径，并简述 PE/PB/股息率与口径。
```

也可本地直接跑：`python scripts/generate_stock_html.py <名称或代码>`  

约定细节见 [`docs/AI协作指南.md`](docs/AI协作指南.md)。

---

## 路线图

- [x] 单票 HTML 复盘页（K 线 + 季报 + 估值）
- [ ] 模板化文字解读 / 口播要点
- [ ] 年限筛选与更多图表积木
- [ ] 板块分析（第二版）
- [ ] 本地数据缓存，减少重复拉取

---

## 免责与使用范围

本项目仅供学习、研究与内容复盘参考，**不构成任何投资建议**。股市有风险，请独立决策并自行承担责任。

仓库为个人学习与复盘用途，**不授权商用**。未经作者书面许可，请勿用于商业产品或付费服务。
