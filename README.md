# 每日网络安全简报

全自动生成每日网络安全情报简报，输出为单页 HTML。

## 工作流程

1. **抓取数据** — `fetch_data.py` 从 RSS 源和 API 抓取原始情报
2. **编写分析** — 根据 `raw_data.json` 手动编写 `analysis.json` 精选条目
3. **生成页面** — `build_page.py` 自动验证数据并生成 `index.html`

## 文件结构

| 文件 | 说明 |
|------|------|
| `SKILL.md` | skill 定义和工作流说明 |
| `fetch_data.py` | 数据抓取脚本（RSS/API） |
| `build_page.py` | 验证 + 页面生成（含自动校验） |
| `raw_data.json` | 原始数据（运行时生成，已 gitignore） |
| `analysis.json` | 分析师精选（运行时生成，已 gitignore） |
| `index.html` | 生成的简报页面 |

## 数据来源

- The Hacker News
- BleepingComputer
- Krebs on Security
- Unit 42
- CISA 安全公告
- Dark Reading
- 嘶吼 RoarTalk
- 先知社区
- 安全内参
- NVD 漏洞库
- 中国网信网

## 使用

```bash
pip install feedparser requests beautifulsoup4

python fetch_data.py
# 手动编写 analysis.json
python build_page.py
```

输出文件：`index.html`
