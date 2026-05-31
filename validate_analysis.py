#!/usr/bin/env python3
"""验证 analysis.json 中所有 URL 均来自 raw_data.json 的真实数据"""
import json, sys, os
sys.stdout.reconfigure(encoding="utf-8")

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
RAW = os.path.join(BASE_DIR, "raw_data.json")
ANALYSIS = os.path.join(BASE_DIR, "analysis.json")

errors = []

raw_data = json.load(open(RAW, encoding="utf-8"))
raw_items = raw_data.get("items", [])
raw_urls = set(it["url"] for it in raw_items)

analysis = json.load(open(ANALYSIS, encoding="utf-8"))
picks = analysis.get("picks", [])

if not picks:
    errors.append("[FAIL] analysis.json 中 picks 为空")

for pick in picks:
    pid = pick.get("id", "?")
    url = pick.get("url", "")
    title = pick.get("title", "")
    source = pick.get("source", "")

    if not url:
        errors.append(f"  [#{pid}] URL 为空: {title}")
        continue

    pick_domain = url.split("/")[2]
    # 检查域名是否匹配 source 对应的真实数据
    source_domains = set(ri["url"].split("/")[2] for ri in raw_items if ri["source"] == source)
    if source_domains and pick_domain not in source_domains:
        errors.append(
            f"  [#{pid}] URL 域名 '{pick_domain}' 与来源 '{source}' 不匹配\n"
            f"         期望域名: {', '.join(sorted(source_domains))}\n"
            f"         URL: {url}\n"
            f"         标题: {title[:60]}"
        )
    elif url not in raw_urls:
        # URL 不在精确列表，但域名匹配，做模糊检查
        matched = False
        for ri in raw_items:
            if url in ri.get("summary", "") or url in ri.get("title", ""):
                matched = True
                break
        if not matched:
            errors.append(
                f"  [#{pid}] URL 在 raw_data.json 中不存在: {url}\n"
                f"         标题: {title[:60]}"
            )

# analysis 检查
for pick in picks:
    text = pick.get("analysis", "")
    clen = len(text)
    if clen < 200 or clen > 400:
        errors.append(f"  [#{pick['id']}] analysis 长度 {clen} 字，要求 200~400 字")

    imp = pick.get("importance", "")
    if imp not in ("★★★★★", "★★★★☆"):
        errors.append(f"  [#{pick['id']}] importance 值非法: {imp}")

    cat = pick.get("category", "")
    valid_cats = {"政策法规", "安全事件", "漏洞风险", "漏洞利用", "解读分析"}
    if cat not in valid_cats:
        errors.append(f"  [#{pick['id']}] category 值非法: {cat}")

if errors:
    print("=" * 60)
    print("  数据验证失败，发现以下问题：")
    print("=" * 60)
    for e in errors:
        print(e)
    print(f"\n  共 {len(errors)} 个问题，请在生成页面前修复！")
    sys.exit(1)
else:
    print(f"  [OK] 验证通过：{len(picks)} 条精选，URL 和字段均合法")
