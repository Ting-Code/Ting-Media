# Ting-Media

个人内容工作台：用工具取数、出图，生成可录屏的竖屏 HTML，并按期归档。

仓库：[https://github.com/Ting-Code/Ting-Media](https://github.com/Ting-Code/Ting-Media)

## 工作流

1. **分析**：先查 `tools/` 是否已有能力并直接调用；同一需求反复出现再封装，避免冗余工具。
2. **出一期**：用对应工具生成 HTML（数据 + 图表），写入 `episodes/<赛道>/YYYY-MM-DD_主题/`。
3. **约定**：见根目录 [`AGENTS.md`](AGENTS.md)。勿手写整页 HTML。

```text
Ting-Media/
├── AGENTS.md
├── episodes/<赛道>/YYYY-MM-DD_主题/
└── tools/
    ├── stock-data/       # 公开市场取数 / 指标序列
    └── stock-analysis/   # 9:16 录屏页
```

### 示例

```bash
cd tools/stock-analysis
pip install -r requirements.txt
pip install -r ../stock-data/requirements.txt
python scripts/generate_stock_html.py <名称或代码>
# -> episodes/<赛道>/YYYY-MM-DD_主题/index.html
```

## 声明

- **生成数据仅供参考**，来自第三方公开源，可能滞后、缺失或有误；**不构成任何决策依据**，使用后果自负。
- **请勿滥用本项目**：不得用于商业售卖、违规营销、向他人提供决策指导或其它违法违规用途。作者不授权商用，不对他人使用后果负责。
- 第三方数据源与依赖库的条款以其官方为准。

## License

个人学习用途；未单独声明商用授权。维护：[@Ting-Code](https://github.com/Ting-Code)
