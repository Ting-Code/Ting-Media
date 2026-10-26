# AI 协作指南

目标：克隆本仓库的人，用 Cursor 等 AI 助手，也能生成结构相近的复盘 HTML。

## 最短路径

1. `pip install -r requirements.txt`
2. 对 AI 发送：

```text
请阅读 AGENTS.md 与 docs/方案.md，用本仓库现有流水线为「<股票名或代码>」生成复盘 HTML，
不要从零手写页面。生成后告诉我 output 路径，并简述 PE/PB/股息率与口径。
```

3. 或手动：`python scripts/generate_stock_html.py <股票名或代码>`
4. 打开 `output/<代码>_<名称>_复盘.html`

## AI 必须遵守

- 走 `scripts/generate_stock_html.py`，复用 `src/market.py` / `fundamentals.py` / `valuation.py` / `render_report.py`
- 不要手写无真实行情的假 K 线页
- 不输出买卖建议；保留免责声明
- 第一版只做单票

## 名称识别

解析顺序见 `src/codes.py`：

1. 内置 `NAME_TO_CODE` 别名  
2. 纯 6 位代码  
3. AkShare A 股简称表（网络可用时）  

仍失败时：让用户提供 6 位代码，或把常用名补进 `NAME_TO_CODE`。

## 常见问题

| 现象 | 处理 |
|------|------|
| BaoStock / 东财 / AkShare 超时或 DNS 失败 | 检查网络与代理后重试；不必改口径 |
| `无法识别股票` | 改用 6 位代码，或补充 `NAME_TO_CODE` |
| HTML 图表空白 | 确认浏览器能访问 Plotly CDN；或检查生成日志是否已 DONE |
| 想改估值锚点 / PE 口径 | 先读 `docs/方案.md` 已确认口径，改前询问用户 |
| 想做板块 | 明确告知第二版，勿编造聚合结果 |

## 验收清单（生成后）

- [ ] 存在 A 行情（可切换日/周/月/季）
- [ ] 存在 B 单季营收/扣非/归母
- [ ] 存在 C 估值序列，且有当前 PE 参考线
- [ ] 页内有免责声明
- [ ] 未把 `output/` 提交进 git
