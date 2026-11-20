# english-pack

自用英语跟读练习工具。打开一个横版练习页，一次只练一句：先听原句，再慢放或循环跟读；英文句里会标出生词和中文意思，也可以把字幕藏起来自己说一遍。

这不是录屏工具，也不会生成 `episodes/` 里的节目页。口播 / 跟读成片请用 `speak-pack`。

## 用法

```bash
cd tools/english-pack
python scripts/generate_practice.py courses/frontend-workplace.json
python scripts/serve_practice.py --port 8781
```

浏览器打开 `http://127.0.0.1:8781/index.html`。建议用本地 HTTP 预览，不要直接用 `file://` 打开，以免个别浏览器限制语音或本地存储。

## 练习时可以做什么

- 选择英语语音、调节语速、循环跟读
- 查看带标记的词汇和中文意思
- 隐藏 / 显示字幕，用来自测
- 点「会了」或「再练」；进度按课程存在本机浏览器（`localStorage`）

快捷键：空格播放或停止，左右方向键换句，`H` 切换字幕。

## 语音说明

跟读使用浏览器自带的语音合成，不录音，也不评分。能否听到英语、声音是否自然，取决于当前浏览器和操作系统是否已安装英语语音包。如果语音列表是空的，请到系统语音设置中安装英语语音后再刷新页面。不支持语音合成的浏览器仍可看字幕练习，但播放和循环会不可用。

句子也可以在课程 JSON 里写可选的本地 `audio` 相对路径；生成时会把音频拷到练习页目录。没有音频时自动用语音合成。

## 换课

课程是 JSON，字段见 [`docs/跟读练习规范.md`](docs/跟读练习规范.md)。第一课是 `courses/frontend-workplace.json`（前端与职场常用句）。新增课程后执行：

```bash
python scripts/generate_practice.py courses/<新课>.json
```

## 测试

```bash
python -m unittest discover -s tests -v
```
