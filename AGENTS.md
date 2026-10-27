# AGENTS.md — Ting-Media

内容工作台：工具取数/出图 → 竖屏录屏 HTML → 按期归档。

## 目录

```text
Ting-Media/
├── AGENTS.md                 # 本文件：约定与工作流（权威）
├── episodes/<赛道>/YYYY-MM-DD_主题/   # 每期产物
└── tools/<工具名>/           # 可运行工具；赛道只用于 episodes 归档
    ├── stock-data/           # 公开市场取数 / 指标序列
    └── stock-analysis/       # 9:16 PPT 录屏 HTML
```

可选的细规范若存在，在对应 `tools/<名>/docs/`；**不必维护公共 docs/**。

## 两条工作流

### 1）数据分析（先查能力，勿乱加工具）

1. 先看现有工具能否覆盖（`stock-data` / `stock-analysis`）。
2. **有能力就直接调用**。
3. **同一类需求反复出现**再封装进 `tools/`；不要一提新需求就新建工具。
4. 单次临时分析：对话/脚本即可，不必先建目录。

### 2）生成一期节目（数据 + 图 → HTML → 归档）

1. 用对应工具取数、出图并生成 HTML（`stock-analysis` → 内部用 `stock-data`）。
2. 写入：`episodes/<赛道>/YYYY-MM-DD_主题/index.html`。
3. **禁止**从零手写整页 HTML；母版固定，只变内容/数据。
4. 竖屏约 9:16；安全区大致顶 12% / 底 18%（具体以 `stock-analysis` 母版为准）。

```bash
cd tools/stock-analysis
pip install -r requirements.txt
pip install -r ../stock-data/requirements.txt
python scripts/generate_stock_html.py <名称或代码> [--theme 主题] [--date YYYY-MM-DD] [--niche finance]
```

## 合规

生成数据仅供参考，不构成决策依据；相关工具不授权商用；请勿滥用。
