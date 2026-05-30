#!/usr/bin/env python3
"""根据原始数据和分析结果生成 HTML 简报页面"""

import json
import os
from datetime import datetime

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
RAW_FILE = os.path.join(BASE_DIR, "raw_data.json")
ANALYSIS_FILE = os.path.join(BASE_DIR, "analysis.json")
OUTPUT_FILE = os.path.join(BASE_DIR, "index.html")

SOURCE_ICONS = {
    "The Hacker News": "📰", "BleepingComputer": "💻",
    "Krebs on Security": "🔍", "Unit 42": "🛡️",
    "CISA 安全公告": "⚠️", "Dark Reading": "📡",
    "嘶吼 RoarTalk": "🇨🇳", "先知社区": "🇨🇳",
    "NVD 漏洞库": "🔴",
}

def load_json(path):
    if not os.path.exists(path):
        print(f"  [X] 文件不存在: {path}")
        return None
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)

def build_html():
    raw = load_json(RAW_FILE)
    analysis = load_json(ANALYSIS_FILE)

    if not raw:
        print("  无原始数据，请先运行 fetch_data.py")
        return

    now = datetime.now()
    date_cn = now.strftime("%Y年%m月%d日")
    weekday = ["一", "二", "三", "四", "五", "六", "日"][now.weekday()]

    all_items = raw.get("items", [])
    curated_items_raw = analysis.get("picks", []) if analysis else []
    curated_items = []
    for it in curated_items_raw:
        curated_items.append({
            "title": it["title"],
            "url": it["url"],
            "source": it["source"],
            "published": it.get("published", ""),
            "summary": it["analysis"],
            "original_title": it.get("original_title", ""),
            "importance": it.get("importance", ""),
            "category": it.get("category", ""),
            "is_cn": True,
        })
    total = len(all_items)

    def render_item(it, is_curated=False):
        icon = SOURCE_ICONS.get(it["source"], "📌")
        score_badge = ""
        if it.get("score", 0) > 0:
            color = "#dc2626" if it["score"] >= 9 else "#ea580c"
            score_badge = f'<span class="score" style="background:{color}">CVSS {it["score"]}</span>'

        title = it.get("title_cn") or it["title"]
        summary = it.get("summary_cn") or it.get("summary", "")

        if is_curated:
            imp = it.get("importance", "")
            cat = it.get("category", "")
            orig = it.get("original_title", "")
            cat_badge = f'<span class="cat-badge">{cat}</span>' if cat else ''
            return f'''<article class="intel-item curated">
  <div class="curated-top">
    <span class="curated-badge">★ 分析师精选</span>
    {cat_badge}
    {"<span class='importance'>" + imp + "</span>" if imp else ""}
  </div>
  <h3><a href="{it["url"]}" target="_blank" rel="noopener">{title}</a>{score_badge}</h3>
  {f'<p class="original-title">原文: {orig}</p>' if orig and orig != title else ''}
  <div class="summary">{summary}</div>
  <div class="meta">
    <span class="source-badge">{icon} {it["source"]}</span>
    {f'<span class="date">发布于 {it["published"]}</span>' if it.get("published") else ''}
    <a class="origin-link" href="{it["url"]}" target="_blank">查看原文 →</a>
  </div>
</article>'''

        return f'''<article class="intel-item">
  <h3><a href="{it["url"]}" target="_blank" rel="noopener">{title}</a>{score_badge}</h3>
  <p class="summary">{summary[:200]}{"..." if len(summary) > 200 else ""}</p>
  <div class="meta">
    <span class="source-badge">{icon} {it["source"]}</span>
    {f'<span class="date">{it.get("published","")}</span>' if it.get("published") else ''}
    <a class="origin-link" href="{it["url"]}" target="_blank">查看原文 →</a>
  </div>
</article>'''

    cur_html = ""

    if curated_items:
        cur_list = "\n".join(render_item(it, True) for it in curated_items)
        cur_html = f'''<section class="source-group curated-section">
  <h2 class="source-title">★ 今日精选情报 <span class="count">({len(curated_items)} 条)</span></h2>
  <p class="curated-desc">以下为 AI 分析师从 {total} 条原始情报中筛选的重要信息，附完整分析总结</p>
  <div class="items">{cur_list}</div>
</section>'''

    html = f'''<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>每日网络安全简报 - {date_cn}</title>
<style>
*, *::before, *::after {{ margin:0; padding:0; box-sizing:border-box; }}
body {{
  font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, "Noto Sans SC", "PingFang SC", sans-serif;
  background: #f0f2f5; color: #1a1a2e; line-height: 1.6;
}}
.header {{
  background: linear-gradient(135deg, #0f0c29, #302b63, #24243e);
  color: #fff; padding: 40px 20px; text-align: center; position: relative; overflow: hidden;
}}
.header::before {{
  content: ''; position: absolute; top:0;left:0;right:0;bottom:0;
  background: radial-gradient(circle at 20% 50%, rgba(0,180,216,0.15) 0%, transparent 50%),
              radial-gradient(circle at 80% 50%, rgba(114,9,183,0.1) 0%, transparent 50%);
}}
.header h1 {{ font-size:1.8em; font-weight:700; position:relative; letter-spacing:2px; }}
.header .subtitle {{ font-size:0.95em; color:rgba(255,255,255,0.7); margin-top:8px; position:relative; }}
.stats-bar {{ display:flex; justify-content:center; gap:40px; margin-top:20px; position:relative; }}
.stat {{ text-align:center; }}
.stat-value {{ font-size:1.8em; font-weight:700; color:#48bfe3; }}
.stat-label {{ font-size:0.8em; color:rgba(255,255,255,0.6); }}
.container {{ max-width:900px; margin:0 auto; padding:24px 16px; }}
.last-update {{ text-align:right; font-size:0.85em; color:#888; margin-bottom:20px; }}

.curated-section {{ margin-bottom:40px; }}
.curated-desc {{ font-size:0.85em; color:#666; margin-bottom:16px; padding-left:4px; }}
.intel-item.curated {{
  border-left: 4px solid #f59e0b;
  background: linear-gradient(135deg, #fffbeb 0%, #fff 100%);
}}
.curated-badge {{
  display: inline-block; background:#f59e0b; color:#fff;
  font-size:0.72em; font-weight:600; padding:2px 10px; border-radius:4px;
  margin-bottom:8px;
}}
.intel-item.curated .summary {{ font-size:0.92em; color:#333; line-height:1.7; }}
.original-title {{ font-size:0.78em; color:#999; margin-bottom:6px; }}
.curated-top {{ display:flex; align-items:center; gap:8px; margin-bottom:8px; flex-wrap:wrap; }}
.cat-badge {{ display:inline-block; background:#e0e7ff; color:#4338ca; font-size:0.72em; font-weight:500; padding:2px 10px; border-radius:4px; }}
.importance {{ font-size:0.8em; color:#f59e0b; letter-spacing:1px; }}

.source-group {{ margin-bottom:32px; }}
.source-title {{
  font-size:1.15em; font-weight:600; color:#1a1a2e;
  padding-bottom:10px; border-bottom:2px solid #e2e8f0;
  margin-bottom:16px; display:flex; align-items:center; gap:8px;
}}
.source-title .count {{ font-size:0.8em; color:#888; font-weight:400; }}
.intel-item {{
  background:#fff; border-radius:10px; padding:18px 20px;
  margin-bottom:12px; box-shadow:0 1px 3px rgba(0,0,0,0.06);
  transition:box-shadow 0.2s, transform 0.15s;
}}
.intel-item:hover {{ box-shadow:0 4px 12px rgba(0,0,0,0.1); transform:translateY(-1px); }}
.intel-item h3 {{
  font-size:1em; font-weight:600; margin-bottom:6px;
  display:flex; align-items:flex-start; gap:8px;
}}
.intel-item h3 a {{ color:#1a1a2e; text-decoration:none; flex:1; }}
.intel-item h3 a:hover {{ color:#4361ee; text-decoration:underline; }}
.score {{
  font-size:0.7em; color:#fff; padding:2px 8px; border-radius:4px;
  white-space:nowrap; flex-shrink:0; margin-top:1px;
}}
.summary {{ font-size:0.88em; color:#555; line-height:1.55; margin-bottom:8px; }}
.meta {{ display:flex; align-items:center; gap:12px; font-size:0.78em; flex-wrap:wrap; }}
.source-badge {{ background:#eef2ff; color:#4361ee; padding:2px 10px; border-radius:12px; font-weight:500; }}
.date {{ color:#999; }}
.origin-link {{ color:#4361ee; text-decoration:none; margin-left:auto; }}
.origin-link:hover {{ text-decoration:underline; }}
.footer {{ text-align:center; padding:30px 20px; color:#999; font-size:0.85em; }}
@media (max-width:600px) {{
  .header h1 {{ font-size:1.4em; }}
  .stats-bar {{ gap:20px; }}
  .stat-value {{ font-size:1.4em; }}
  .intel-item {{ padding:14px 16px; }}
  .intel-item h3 {{ font-size:0.95em; }}
}}
</style>
</head>
<body>
<div class="header">
  <h1>🛡️ 每日网络安全简报</h1>
  <p class="subtitle">{date_cn} 星期{weekday} · AI 分析师精选</p>
  <div class="stats-bar">
    <div class="stat"><div class="stat-value">{total}</div><div class="stat-label">情报条目</div></div>
    <div class="stat"><div class="stat-value">{len(set(it['source'] for it in all_items))}</div><div class="stat-label">数据来源</div></div>
    {f'<div class="stat"><div class="stat-value">{len(curated_items)}</div><div class="stat-label">精选推荐</div></div>' if curated_items else ''}
  </div>
</div>
<div class="container">
  <p class="last-update">🔄 更新于 {raw["fetched_at"]}</p>

  {cur_html}
</div>
<div class="footer">
  <p>每日网络安全简报 | 精选内容由 AI 分析师从 RSS Feed 原始数据中筛选撰写</p>
  <p style="margin-top:4px;">数据源: {' · '.join(sorted(set(it['source'] for it in all_items)))}</p>
</div>
</body>
</html>'''
    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        f.write(html)
    print(f"  [OK] 已生成: {OUTPUT_FILE} ({len(html):,} 字节)")

if __name__ == "__main__":
    build_html()
