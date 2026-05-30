# 每日网络安全简报

AI skill — 全自动每日网络安全简报生成。

对 AI 助手说"做安全简报"，即可自动完成：**数据抓取 → AI 情报分析 → 生成 HTML 页面**。

## 前置依赖

- [opencode](https://opencode.ai) 或 [Claude Code](https://docs.anthropic.com/en/docs/claude-code/overview)（支持 skills 机制的 AI 助手）
- Python >= 3.7
- （可选）[Kimi WebBridge](https://kimi.com/features/webbridge) — 用于浏览器补抓

## 安装

### 1. 下载技能

```bash
git clone https://github.com/你的用户名/security-briefing.git
```

### 2. 复制到技能目录

**opencode:**

| 平台 | 命令 |
|------|------|
| Windows | `xcopy /E security-briefing %USERPROFILE%\.agents\skills\security-briefing\` |
| Mac / Linux | `cp -r security-briefing ~/.agents/skills/security-briefing/` |

**Claude Code:**

| 平台 | 命令 |
|------|------|
| Windows | `xcopy /E security-briefing %USERPROFILE%\.claude\skills\security-briefing\` |
| Mac / Linux | `cp -r security-briefing ~/.claude/skills/security-briefing/` |

### 3. 确认安装

在 AI 助手中输入以下任意指令，触发技能自动工作：

> 做安全简报
> 今天的安全情报
> security briefing

## 配置

（可选）安装 Kimi WebBridge 可在 RSS 直连失败时通过浏览器补抓。

## 工作原理

```
用户触发 → pip install (自动) → fetch_data.py (RSS + NVD) → 浏览器补抓 (可选)
→ AI 分析写 analysis.json → build_page.py → index.html
```

### 数据源

- The Hacker News
- BleepingComputer
- Krebs on Security
- Dark Reading
- Unit 42
- 先知社区
- 嘶吼 RoarTalk
- 安全内参
- NVD 漏洞库

### 输出

生成的 `index.html` 是单页深色主题 HTML，包含：
- 深色渐变头部（日期 + 统计概览）
- 精选情报卡片（完整分析段落 + 分类 + 评级）
- 响应式设计，手机端友好

## License

MIT
