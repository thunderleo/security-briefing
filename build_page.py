#!/usr/bin/env python3
"""根据原始数据和分析结果生成 HTML 简报页面"""

import json, os, sys, re, html, shutil
from datetime import datetime
from string import Template

def hex_to_rgba(hex_color, alpha=0.1):
    h = hex_color.lstrip("#")
    r, g, b = int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16)
    return f"rgba({r},{g},{b},{alpha})"

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
    "安全内参": "🇨🇳",
}

CATEGORY_ORDER = ["政策法规", "安全事件", "漏洞风险", "漏洞利用", "解读分析"]
CATEGORY_CONFIG = {
    "漏洞利用": {"icon": "🎯", "color": "#dc2626"},
    "漏洞风险": {"icon": "⚠️", "color": "#ea580c"},
    "安全事件": {"icon": "🚨", "color": "#d97706"},
    "政策法规": {"icon": "📜", "color": "#2563eb"},
    "解读分析": {"icon": "🔍", "color": "#7c3aed"},
}

def load_json(path):
    if not os.path.exists(path):
        print(f"  [X] 文件不存在: {path}")
        return None
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)

VALID_CATS = {"政策法规", "安全事件", "漏洞风险", "漏洞利用", "解读分析"}
VALID_IMPS = {"★★★★★", "★★★★☆"}

def validate(picks, raw_items):
    errors = []
    raw_urls = set(it["url"] for it in raw_items)

    for pick in picks:
        pid = pick.get("id", "?")
        url = pick.get("url", "")
        title = pick.get("title", "")
        source = pick.get("source", "")

        if not url:
            errors.append(f"  [#{pid}] URL 为空")
            continue

        pick_domain = url.split("/")[2]
        source_domains = set(ri["url"].split("/")[2] for ri in raw_items if ri["source"] == source)
        if source_domains and pick_domain not in source_domains:
            errors.append(
                f"  [#{pid}] URL 域名 '{pick_domain}' 与来源 '{source}' 不匹配\n"
                f"         期望域名: {', '.join(sorted(source_domains))}"
            )
        elif url not in raw_urls:
            matched = any(url in ri.get("summary", "") or url in ri.get("title", "") for ri in raw_items)
            if not matched:
                errors.append(f"  [#{pid}] URL 在 raw_data.json 中不存在: {url}")

        text = pick.get("analysis", "")
        clen = len(text)
        if clen < 200 or clen > 400:
            errors.append(f"  [#{pid}] analysis 长度 {clen} 字，要求 200~400 字")

        imp = pick.get("importance", "")
        if imp not in VALID_IMPS:
            errors.append(f"  [#{pid}] importance 值非法: {imp}")

        cat = pick.get("category", "")
        if cat not in VALID_CATS:
            errors.append(f"  [#{pid}] category 值非法: {cat}")

    return errors

def build_html():
    raw = load_json(RAW_FILE)
    analysis = load_json(ANALYSIS_FILE)

    if not raw:
        print("  无原始数据，请先运行 fetch_data.py")
        return

    if analysis:
        picks = analysis.get("picks", [])
        errors = validate(picks, raw.get("items", []))
        if errors:
            print("=" * 60)
            print("  [FAIL] 数据验证不通过，请修复以下问题：")
            print("=" * 60)
            for e in errors:
                print(e)
            print()
            sys.exit(1)
        print(f"  [OK] 验证通过：{len(picks)} 条精选")
    else:
        print("  无分析数据，仅显示原始条目")

    now = datetime.now()
    date_cn = now.strftime("%Y年%m月%d日")
    weekday = ["一", "二", "三", "四", "五", "六", "日"][now.weekday()]

    all_items = raw.get("items", [])
    raw_published = {it["url"]: (it.get("published", "") or "")[:10] for it in all_items}
    curated_items_raw = analysis.get("picks", []) if analysis else []
    curated_items = []
    for it in curated_items_raw:
        curated_items.append({
            "title": it["title"],
            "url": it["url"],
            "source": it["source"],
            "published": (raw_published.get(it["url"], "") or "")[:10],
            "summary": it["analysis"],
            "original_title": it.get("original_title", ""),
            "importance": it.get("importance", ""),
            "category": it.get("category", ""),
            "original_category": it.get("original_category", ""),
            "is_cn": True,
        })
    total = len(all_items)

    def render_item(it, is_curated=False):
        icon = SOURCE_ICONS.get(it["source"], "📌")
        score_badge = ""
        if it.get("score", 0) > 0:
            color = "#dc2626" if it["score"] >= 9 else "#ea580c"
            score_badge = f'<span class="score" style="background:{color}">CVSS {it["score"]}</span>'

        title = html.escape(it.get("title_cn") or it["title"])
        summary = html.escape(it.get("summary_cn") or it.get("summary", ""))

        if is_curated:
            imp = it.get("importance", "")
            orig = html.escape(it.get("original_title", ""))
            section_cat = it.get("category", "")
            cat_cfg = CATEGORY_CONFIG.get(section_cat, {"color": "#666"})
            orig_cat = it.get("original_category", "")
            badge_label = html.escape(orig_cat or section_cat)
            safe_url = html.escape(it["url"])
            safe_source = html.escape(it["source"])
            safe_pub = html.escape(it.get("published") or date_cn)
            cat_badge = f'<span class="cat-badge" style="background:{hex_to_rgba(cat_cfg["color"])};color:{cat_cfg["color"]}">{badge_label}</span>'
            return f'''<article class="intel-item curated">
  <div class="curated-top">
    <span class="curated-badge">★ 分析师精选</span>
    {cat_badge}
    {"<span class='importance'>" + imp + "</span>" if imp else ""}
  </div>
  <h3><a href="{safe_url}" target="_blank" rel="noopener">{title}</a>{score_badge}</h3>
  {f'<p class="original-title">原文: {orig}</p>' if orig and orig != title else ''}
  <div class="summary">{summary}</div>
  <div class="meta">
    <span class="source-badge">{icon} {safe_source}</span>
    <span class="date">发布于 {safe_pub}</span>
    <a class="origin-link" href="{safe_url}" target="_blank" rel="noopener">查看原文 →</a>
  </div>
</article>'''

        safe_url = html.escape(it["url"])
        safe_source = html.escape(it["source"])
        safe_pub = html.escape(it.get("published") or date_cn)
        return f'''<article class="intel-item">
  <h3><a href="{safe_url}" target="_blank" rel="noopener">{title}</a>{score_badge}</h3>
  <p class="summary">{summary[:200]}{"..." if len(summary) > 200 else ""}</p>
  <div class="meta">
    <span class="source-badge">{icon} {safe_source}</span>
    <span class="date">{safe_pub}</span>
    <a class="origin-link" href="{safe_url}" target="_blank" rel="noopener">查看原文 →</a>
  </div>
</article>'''

    cur_html = ""

    if curated_items:
        from collections import OrderedDict
        grouped = OrderedDict()
        for cat in CATEGORY_ORDER:
            grouped[cat] = []
        for it in curated_items:
            cat = it.get("category", "")
            if cat in grouped:
                grouped[cat].append(it)

        sections = []
        for cat, items in grouped.items():
            if not items:
                continue
            cfg = CATEGORY_CONFIG.get(cat, {"icon": "📌", "color": "#666"})
            item_html = "\n".join(render_item(it, True) for it in items)
            sections.append(f'''<section class="cat-section" style="border-top:3px solid {cfg['color']};">
  <h2 class="cat-section-title">{cfg['icon']} {cat} <span class="count">({len(items)} 条)</span></h2>
  <div class="items">{item_html}</div>
</section>''')

        cur_html = f'''<p class="curated-intro">以下为 AI 分析师从 {total} 条原始情报中筛选的重要信息，按分类展示</p>
{"".join(sections)}'''

    og_desc = f"AI 分析师从 {total} 条情报中精选 {len(curated_items)} 条安全要闻，涵盖政策法规、安全事件、漏洞风险等"
    curated_stat_html = (f'<div class="stat"><div class="stat-value">{len(curated_items)}</div><div class="stat-label">精选推荐</div></div>'
                         if curated_items else '')

    tmpl_path = os.path.join(BASE_DIR, "template.html")
    with open(tmpl_path, encoding="utf-8") as f:
        tmpl = Template(f.read())

    page_html = tmpl.safe_substitute(
        TITLE=date_cn,
        OG_TITLE=html.escape(date_cn),
        OG_DESC=og_desc,
        SUBTITLE=f"{date_cn} 星期{weekday} · AI 分析师精选",
        TOTAL_ITEMS=str(total),
        SOURCE_COUNT=str(len(set(it['source'] for it in all_items))),
        CURATED_STAT=curated_stat_html,
        CURATED_HTML=cur_html or "",
        LAST_UPDATE=raw["fetched_at"],
        SOURCE_LIST=" · ".join(sorted(set(it['source'] for it in all_items))),
    )
    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        f.write(page_html)

    date_label = datetime.now().strftime("%Y-%m-%d")

    if analysis and os.path.exists(ANALYSIS_FILE):
        analysis_dir = os.path.join(BASE_DIR, "analysis")
        os.makedirs(analysis_dir, exist_ok=True)
        analysis_path = os.path.join(analysis_dir, f"{date_label}.json")
        if not os.path.exists(analysis_path):
            shutil.copy2(ANALYSIS_FILE, analysis_path)

    html_dir = os.path.join(BASE_DIR, "archive")
    os.makedirs(html_dir, exist_ok=True)
    html_path = os.path.join(html_dir, f"{date_label}.html")
    with open(html_path, "w", encoding="utf-8") as f:
        f.write(page_html)

    dates = sorted(set(
        f.removesuffix(".html") for f in os.listdir(html_dir)
        if f.endswith(".html") and f != "index.html"
    ), reverse=True)
    links = "\n".join(
        f'    <li><a href="{d}.html">{d}</a></li>' for d in dates
    )
    archive_html = f"""<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>每日网络安全简报 - 历史归档</title>
<style>
body {{ font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, "Noto Sans SC", sans-serif; background: #f0f2f5; color: #1a1a2e; line-height: 1.6; max-width: 600px; margin: 0 auto; padding: 40px 20px; }}
h1 {{ font-size: 1.5em; margin-bottom: 8px; }}
p {{ color: #666; margin-bottom: 24px; }}
ul {{ list-style: none; padding: 0; }}
li {{ padding: 8px 0; }}
a {{ color: #4361ee; text-decoration: none; }}
a:hover {{ text-decoration: underline; }}
</style>
</head>
<body>
<h1>📅 历史归档</h1>
<p>共 {len(dates)} 期简报</p>
<ul>
{links}
</ul>
</body>
</html>"""
    with open(os.path.join(html_dir, "index.html"), "w", encoding="utf-8") as f:
        f.write(archive_html)

    print(f"  [OK] 已生成: {OUTPUT_FILE} ({len(page_html):,} 字节)")

if __name__ == "__main__":
    build_html()
