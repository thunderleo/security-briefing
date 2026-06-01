---
name: security-briefing
description: 全自动每日网络安全简报生成。用户说"做安全简报"或类似指令时触发，由我自主完成数据抓取、情报分析、页面生成全部环节，用户只需最后打开页面查看。绝不要求用户先运行任何脚本。触发词：安全简报、情报分析、security briefing、今天的安全、今日情报。
---

# 全自动每日网络安全简报

SKILL_DIR 为此文档所在目录。所有脚本和数据文件均在此目录中，脚本通过 `os.path.dirname(__file__)` 自动定位自身。

## 前提条件

- Python 3.7+
- （可选）Kimi WebBridge — 用于浏览器补抓

## 平台约定

| 操作 | Windows | Mac / Linux |
|------|---------|-------------|
| Python 命令 | `python` | `python3` |
| pip 命令 | `python -m pip` | `python3 -m pip` |

## 工作流程

### 第零步：自动安装依赖

```bash
python[3] -m pip install feedparser requests beautifulsoup4 -q
```

可执行多次，已安装的包秒过，不阻塞流程。

### 第一步：数据抓取

1. **运行脚本** — 按平台约定执行 `python[3] SKILL_DIR/fetch_data.py`
2. **检查缺失源** — 查看 `raw_data.json` 中以下来源是否缺失：BleepingComputer、嘶吼、NVD、Krebs on Security、模安局
3. **浏览器补抓** — 先检查 Kimi WebBridge 是否正常运行（`kimi-webbridge status`）。若正常，对缺失源用浏览器访问 RSS feed 获取内容；若不可用，跳过此步骤，缺失源不纳入本期简报
4. **合并数据** — 浏览器抓取结果格式化为一致结构，追加写入 `raw_data.json`

### 第二步：编写分析

读取 `raw_data.json`，按下方规范写入 `analysis.json`。

**⚠️ URL 必须从 raw_data.json 中提取真实链接**，不可凭标题推测生成。可用以下方式查看 URL：
```bash
python[3] -c "import json; d=json.load(open('SKILL_DIR/raw_data.json')); [print(f'{i}. [{it[\"source\"]}] {it[\"title\"][:60]}\n   {it[\"url\"]}') for i,it in enumerate(d['items'],1)]"
```

### 第三步：生成页面

1. 按平台约定执行 `python[3] SKILL_DIR/build_page.py` — 自动**验证数据 → 生成 HTML** 一步完成
2. 验证失败则中止，根据提示修复 `analysis.json` 后重试
3. 告知用户页面路径：`SKILL_DIR/index.html`

## 分析编写规范

### 格式

```json
{
  "id": 序号,
  "title": "中文标题（自拟，含关键信息）",
  "original_title": "原始英文标题",
  "url": "原文链接",
  "source": "来源名称",
  "importance": "★★★★★",
  "category": "分类（五大类之一：政策法规/安全事件/漏洞风险/漏洞利用/解读分析）",
  "original_category": "原始精细分类（如漏洞预警/新型攻击/数据泄露等）",
  "analysis": "完整分析段落（200~400 字）"
}
```

### 字段规则

- **title**: 自拟中文标题，包含 CVE 编号/组织名/产品名
- **original_title**: 英文源保留原文
- **source**: 从 raw 中直接取
- **importance**: ★★★★★ 或 ★★★★☆
- **category**: `政策法规` `安全事件` `漏洞风险` `漏洞利用` `解读分析`
- **original_category**: 保留原始的精细分类（如 `漏洞预警` `新型攻击` `数据泄露` `执法行动` `安全趋势` `安全技术` `供应链安全` `威胁情报` 等），在卡片右下角以彩色标签显示

### analysis 段落要求

每条 200~400 汉字，包括：
1. **事件概要** — 发生了什么（1-2 句）
2. **影响分析** — 谁受影响、严重程度
3. **行动建议** — 防御方可操作步骤
4. **全局视角** — 关联同类事件或行业趋势

风格：专业但可读，适合安全从业者晨读。CVSS 以 `CVSS X.X` 格式标注。

### 精选原则

- 优先：政策法规、安全事件、国内生态相关、新型攻击手法
- 覆盖：不同来源和分类的分布平衡
- 同一事件多源报道时合并为一条
- 国内：涉及政策法规、安全事件、国内产品品牌等要高度重视
- 数量：每次精选约 20 条，根据当日情报质量在 15~25 条范围内浮动

## 验证

以上检查由 `build_page.py` 自动完成，不通过则拒绝生成页面：

- JSON 格式合法
- 每条 `url` 域名与来源匹配，且在 `raw_data.json` 中有对应条目
- 每条 analysis 200~400 汉字
- importance 只出现 ★★★★★ 和 ★★★★☆
- category 在指定集合中

## 附录：手动生成 HTML

若 `build_page.py` 不可用，手动生成：
1. 读取 `analysis.json` 的 `picks` 数组
2. 读取 `raw_data.json` 获取来源统计
3. 生成单页 HTML，结构：深色渐变头部、精选情报卡片区、来源统计脚注
4. 写入 `index.html`
