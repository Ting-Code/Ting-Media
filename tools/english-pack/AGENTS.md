# AGENTS.md — tools/english-pack

自用英语跟读练习工具。横版练习页，一次只练一句。**不是** 9:16 录屏页，也**不要**写入 `episodes/`。不要改 `speak-pack` / `screen-pack` 的母版。

- **练习规范**：[`docs/跟读练习规范.md`](docs/跟读练习规范.md)
- **换课只换课程 JSON**，练习页模板可直接维护（不要把「禁止手写整页 HTML」套用到本工具）
- 语音只用浏览器 `speechSynthesis`，可选附带本地音频；不录音、不评分，不调用付费 API

```bash
cd tools/english-pack
python scripts/generate_practice.py courses/frontend-workplace.json
python scripts/serve_practice.py --port 8781
# -> http://127.0.0.1:8781/index.html
```

练习页写入 `tools/english-pack/practice/<课程id>/index.html`。

```bash
python -m unittest discover -s tests -v
```
