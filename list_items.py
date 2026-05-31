#!/usr/bin/env python3
"""打印原始数据条目，供 AI 分析师筛选素材用

用法:
  python list_items.py              # 列出全部
  python list_items.py --search CVE  # 按关键词筛选
  python list_items.py --show-url    # 显示 URL
"""

import json, sys, os
sys.stdout.reconfigure(encoding="utf-8")

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
RAW = os.path.join(BASE_DIR, "raw_data.json")

show_url = "--show-url" in sys.argv
search = None
for i, arg in enumerate(sys.argv):
    if arg == "--search" and i + 1 < len(sys.argv):
        search = sys.argv[i + 1].lower()

data = json.load(open(RAW, encoding="utf-8"))
count = 0
for i, item in enumerate(data["items"], 1):
    if search and search not in item["title"].lower() and search not in item["source"].lower():
        continue
    count += 1
    print(f"{i:2d}. [{item['source']}] {item['title']}")
    if show_url:
        print(f"    URL: {item['url']}")
    print(f"    {item['summary'][:120]}...")
    print()

if search:
    print(f"  [{count} 条匹配 '{search}']")
print(f"  共 {len(data['items'])} 条原始数据")
