#!/usr/bin/env python3
"""抓取网络安全情报原始数据，保存为 JSON"""

import feedparser
import requests
import json
import re
import os
import hashlib
from datetime import datetime, timezone, timedelta
from bs4 import BeautifulSoup

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
RAW_FILE = os.path.join(BASE_DIR, "raw_data.json")

session = requests.Session()

RSS_FEEDS = {
    "The Hacker News": "https://feeds.feedburner.com/TheHackersNews",
    "BleepingComputer": "https://www.bleepingcomputer.com/feed/",
    "Krebs on Security": "https://krebsonsecurity.com/feed/",
    "Unit 42": "https://feeds.feedburner.com/Unit42",
    "CISA 安全公告": "https://www.cisa.gov/cybersecurity-advisories/cybersecurity-advisories.xml",
    "Dark Reading": "https://www.darkreading.com/rss.xml",
    "嘶吼 RoarTalk": "https://www.4hou.com/feed",
    "先知社区": "https://xz.aliyun.com/feed",
}

NVD_API_URL = "https://services.nvd.nist.gov/rest/json/cves/2.0"

MAX_PER_SOURCE = 8
HOURS_BACK = 72

def clean_html(text):
    if not text:
        return ""
    soup = BeautifulSoup(text, "html.parser")
    text = soup.get_text(separator=" ", strip=True)
    return re.sub(r'\s+', ' ', text)[:500]

def fetch_rss(url, name, is_cn=False):
    items = []
    try:
        if is_cn:
            feed = feedparser.parse(url)
        else:
            resp = session.get(url, timeout=15)
            feed = feedparser.parse(resp.content)
        if feed.bozo and not feed.entries:
            return items
        now = datetime.now(timezone.utc)
        cutoff = now - timedelta(hours=HOURS_BACK)
        for entry in feed.entries[:MAX_PER_SOURCE]:
            pub = None
            if hasattr(entry, "updated_parsed") and entry.updated_parsed:
                pub = datetime(*entry.updated_parsed[:6], tzinfo=timezone.utc)
            elif hasattr(entry, "published_parsed") and entry.published_parsed:
                pub = datetime(*entry.published_parsed[:6], tzinfo=timezone.utc)
            if pub and pub < cutoff and not is_cn:
                continue
            summary = ""
            if hasattr(entry, "summary") and entry.summary:
                summary = entry.summary
            elif hasattr(entry, "description") and entry.description:
                summary = entry.description
            if hasattr(entry, "content") and entry.content:
                summary = entry.content[0].get("value", "") or summary
            items.append({
                "title": entry.get("title", "").strip(),
                "url": entry.get("link", ""),
                "summary": clean_html(summary),
                "source": name,
                "published": pub.strftime("%Y-%m-%d %H:%M UTC") if pub else "",
                "is_cn": is_cn,
            })
    except Exception as e:
        print(f"  [X] {name}: {e}")
    return items

def fetch_nvd():
    items = []
    now = datetime.now(timezone.utc)
    start = now - timedelta(hours=HOURS_BACK)
    params = {
        "pubStartDate": start.strftime("%Y-%m-%dT%H:%M:%S.000"),
        "pubEndDate": now.strftime("%Y-%m-%dT%H:%M:%S.000"),
        "cvssV3Severity": "HIGH",
        "resultsPerPage": 10,
    }
    try:
        resp = session.get(NVD_API_URL, params=params, timeout=30)
        resp.raise_for_status()
        data = resp.json()
        for vuln in data.get("vulnerabilities", []):
            cve = vuln.get("cve", {})
            desc = ""
            for d in cve.get("descriptions", []):
                if d.get("lang") == "en":
                    desc = d["value"]
                    break
            metrics = cve.get("metrics", {})
            cvss = 0.0
            for ver in ["cvssMetricV31", "cvssMetricV30", "cvssMetricV2"]:
                if ver in metrics:
                    cvss = metrics[ver][0]["cvssData"].get("baseScore", 0)
                    break
            items.append({
                "title": cve.get("id", ""),
                "url": f"https://nvd.nist.gov/vuln/detail/{cve.get('id','')}",
                "summary": desc[:500] if desc else "",
                "source": "NVD 漏洞库",
                "published": cve.get("published", "")[:10] if cve.get("published") else "",
                "score": cvss,
                "is_cn": False,
            })
    except Exception as e:
        print(f"  [X] NVD: {e}")
    return items

def main():
    print("=" * 50)
    print("  [抓取] 安全情报原始数据")
    print(f"  {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 50)

    all_items = []

    print("\n  英文源...")
    for name, url in RSS_FEEDS.items():
        if name in ["嘶吼 RoarTalk", "先知社区"]:
            continue
        items = fetch_rss(url, name)
        print(f"    {name}: {len(items)}")
        all_items.extend(items)

    print("\n  中文源...")
    for name, url in RSS_FEEDS.items():
        if name not in ["嘶吼 RoarTalk", "先知社区"]:
            continue
        items = fetch_rss(url, name, is_cn=True)
        print(f"    {name}: {len(items)}")
        all_items.extend(items)

    print("\n  NVD 漏洞...")
    nvd = fetch_nvd()
    print(f"    NVD: {len(nvd)}")
    all_items.extend(nvd)

    seen = set()
    unique = []
    for it in all_items:
        key = hashlib.md5((it["title"] + it["source"]).encode()).hexdigest()
        if key not in seen:
            seen.add(key)
            unique.append(it)

    data = {
        "fetched_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "total": len(unique),
        "items": unique,
    }

    with open(RAW_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

    print(f"\n  [OK] 已保存 {len(unique)} 条到 {RAW_FILE}")
    print("=" * 50)

if __name__ == "__main__":
    main()
