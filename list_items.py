#!/usr/bin/env python3
"""打印原始数据条目，供 AI 分析师筛选素材用"""
import json, sys, os
sys.stdout.reconfigure(encoding="utf-8")

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
RAW = os.path.join(BASE_DIR, "raw_data.json")

data = json.load(open(RAW, encoding="utf-8"))
for i, item in enumerate(data["items"], 1):
    print(f"{i:2d}. [{item['source']}] {item['title']}")
    print(f"    {item['summary'][:120]}...")
    print()
