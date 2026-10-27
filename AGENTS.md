# AGENTS.md — Ting-Media

自媒体录屏工作台。目录见 `docs/目录规划.md`。

## 两条工作流

### 1）金融相关分析（先查能力，勿乱加工具）

1. 先看现有工具能否覆盖（当前：`tools/stock-data` 取数/估值序列；`tools/stock-analysis` 出录屏页）。
2. **有能力就直接调用**，在对话里完成分析或出数即可。
3. **只有同一类需求反复出现**，再考虑封装进 `tools/`；不要一提新需求就新建工具或堆冗余文档。
4. 单次临时分析：可用脚本/对话，不必先建目录。

### 2）生成一期节目（数据 + 图 → HTML → 归档）

1. 用对应工具取数、出图并生成 HTML（财经复盘用 `stock-analysis`，其内部调用 `stock-data`）。
2. 遵守该工具规范（如 `tools/stock-analysis/docs/9-16-录屏规范.md`）。
3. 写入：`episodes/<赛道>/YYYY-MM-DD_主题/index.html`。
4. **禁止**从零手写整页 HTML；母版固定，只变内容/数据。

```bash
cd tools/stock-analysis
pip install -r requirements.txt
pip install -r ../stock-data/requirements.txt
python scripts/generate_stock_html.py <名称或代码> [--theme 主题] [--date YYYY-MM-DD] [--niche finance]
```

## 现有工具

| 工具 | 能力 |
|------|------|
| `tools/stock-data` | A 股行情/季报/分红/估值序列（`docs/数据源规范.md`） |
| `tools/stock-analysis` | 9:16 PPT 录屏 HTML（`docs/9-16-录屏规范.md`） |

合规：科普/复盘，不荐股；相关工具不授权商用。
