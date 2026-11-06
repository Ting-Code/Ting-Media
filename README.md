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
    ├── screen-pack/    # 9:16 录屏页
    ├── stock-screener/    # 全 A 技术面选股
    ├── platform-trends/   # 跨平台热榜（B站/微博/抖音）
    └── interactive-pack/  # 互动离线 HTML（抖音/B站Toy/小红书）
```

### 示例

```bash
cd tools/screen-pack
pip install -r requirements.txt
pip install -r ../stock-data/requirements.txt
python scripts/generate_stock_html.py <名称或代码>
# -> episodes/<赛道>/YYYY-MM-DD_主题/index.html
```


跨平台热度（B站作品 / 微博热搜 / 抖音热词；默认只出数据摘要）：

```bash
cd tools/platform-trends
pip install -r requirements.txt
python scripts/analyze_trends.py
```



互动离线包（写入同一期 `episodes/<赛道>/YYYY-MM-DD_主题/`）：

```bash
cd tools/interactive-pack
python scripts/cli.py --platform common generate 
  --content examples/sample.json 
  --theme 今日热度速览 --date 2026-11-05 --niche finance
```

## 声明

- **生成数据仅供参考**，来自第三方公开源，可能滞后、缺失或有误；**不构成任何决策依据**，使用后果自负。
- **请勿滥用本项目**：不得用于商业售卖、违规营销、向他人提供决策指导或其它违法违规用途。作者不授权商用，不对他人使用后果负责。
- 第三方数据源与依赖库的条款以其官方为准。

## License

个人学习用途；未单独声明商用授权。维护：[@Ting-Code](https://github.com/Ting-Code)
