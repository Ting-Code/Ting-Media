# AI 协作指南

目标：用现有流水线生成结构相近的录屏 HTML。

提示词示例：

```text
请阅读 AGENTS.md，用现有流水线为「<名称或代码>」生成录屏 HTML，
不要从零手写页面。完成后给出产物路径。
```

步骤：
1. 读本工具 `AGENTS.md`
2. `python scripts/generate_stock_html.py <名称或代码>`
3. 产物写入 `episodes/...`（或本地 `output/` 中间结果）

约束：走现有脚本与 `stock-data`；不要手写无真实数据的假页。生成数据仅供参考。
