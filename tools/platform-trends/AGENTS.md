# AGENTS.md — tools/platform-trends

跨平台热度：看**平台上什么在火**，不是自己账号后台。

一期免 Key 三家：B站热门作品、微博热搜、抖音热词。小红书 / 视频号未接入。

**默认只输出数据摘要**（控制台）。未明确要求录屏节目时，不要生成 HTML。

- 数据规范：[`docs/数据源规范.md`](docs/数据源规范.md)
- 仅当用户明确要录屏节目时，才加 `--html`（复用 `screen-pack` 9:16 母版）

```bash
cd tools/platform-trends
pip install -r requirements.txt
python scripts/analyze_trends.py
python scripts/analyze_trends.py --platform bilibili,weibo --top 15
python scripts/analyze_trends.py --json
# -> cache/trends_YYYY-MM-DD/
# 仅录屏节目（成片 episodes/…，缓存 cache/日期_主题/）：
python scripts/analyze_trends.py --html --theme 今日热度 --date YYYY-MM-DD
```

生成数据仅供参考；不授权商用；请勿滥用。

## 互动上传页

录屏用本工具 `--html`；要上传抖音/B站Toy/小红书互动空间，改走 `tools/interactive-pack`（离线包规范不同）。
