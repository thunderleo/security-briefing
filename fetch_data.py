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
import urllib.parse

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
RAW_FILE = os.path.join(BASE_DIR, "raw_data.json")

session = requests.Session()
session.headers.update({"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"})

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
HOURS_BACK = 168

def clean_html(text):
    if not text:
        return ""
    soup = BeautifulSoup(text, "html.parser")
    text = soup.get_text(separator=" ", strip=True)
    return re.sub(r'\s+', ' ', text)[:500]

def fetch_rss(url, name, is_cn=False):
    items = []
    feed = None
    for attempt in range(2):
        try:
            if is_cn:
                feed = feedparser.parse(url)
            else:
                resp = session.get(url, timeout=15)
                feed = feedparser.parse(resp.content)
            break
        except Exception as e:
            if attempt == 0:
                print(f"  [R] {name}: 重试...")
                continue
            print(f"  [X] {name}: {e}")
            return items
    if feed is None or (feed.bozo and not feed.entries):
        return items
    now = datetime.now(timezone.utc)
    cutoff = now - timedelta(hours=HOURS_BACK)
    for entry in feed.entries[:MAX_PER_SOURCE]:
        try:
            pub = None
            if hasattr(entry, "updated_parsed") and entry.updated_parsed:
                pub = datetime(*entry.updated_parsed[:6], tzinfo=timezone.utc)
            elif hasattr(entry, "published_parsed") and entry.published_parsed:
                pub = datetime(*entry.published_parsed[:6], tzinfo=timezone.utc)
            if pub and pub < cutoff:
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
        except Exception:
            continue
    return items

def fetch_secrss():
    items = []
    for page in [1, 2, 3]:
        try:
            resp = session.get(f"https://www.secrss.com/api/articles?page={page}&per-page=20", timeout=15)
            resp.raise_for_status()
            data = resp.json()
            if data.get("code") != "10000":
                continue
            for art in data.get("data", []):
                title = (art.get("title") or "").strip()
                if not title:
                    continue
                pub = art.get("published_at", "")
                items.append({
                    "title": title,
                    "url": f"https://www.secrss.com/articles/{art['id']}",
                    "summary": (art.get("summary") or "")[:500],
                    "source": "安全内参",
                    "published": pub,
                    "is_cn": True,
                })
        except Exception as e:
            print(f"  [X] 安全内参 page {page}: {e}")

    for item in items[:20]:
        try:
            resp = session.get(item["url"], timeout=15)
            soup = BeautifulSoup(resp.text, "html.parser")
            body = soup.select_one(".article-body")
            if body:
                text = body.get_text(strip=True)
                if len(text) > len(item["summary"]):
                    item["summary"] = text[:1000]
        except:
            pass
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

CAC_URL = "https://www.cac.gov.cn/index.htm"
CAC_SOURCE = "中国网信网"
CAC_KEEP = [
    "网信", "安全", "网络", "数据", "信息", "法规", "规定", "办法",
    "通知", "意见", "指南", "标准", "监管", "治理", "合规",
    "清朗", "整治", "专项行动", "备案",
    "数字素养", "信息化", "人工智能", "算法", "互联网",
    "个人信息", "数据出境", "网络暴力", "网络谣言",
    "算法推荐", "深度合成", "生成式",
    "个人信息保护", "网络安全",
    "网络执法", "网络举报", "网络法治",
]
CAC_SKIP = [
    "设为首页", "加入收藏", "手机版",
    "主任信箱", "返回顶部", "学习强国",
    "相关链接", "联系我们", "网站地图",
    "登录", "注册", "搜索", "English",
    "专题", "专 题",
]

def is_valid_cac_item(text, href):
    if not text or not href:
        return False
    if not href.startswith("https://www.cac.gov.cn"):
        return False
    if any(sk in text for sk in CAC_SKIP):
        return False
    if re.search(r"(\.(jpg|png|gif|pdf|docx?|xlsx?|zip))$", href, re.I):
        return False
    if "javascript:" in href:
        return False
    return True

def fetch_cac():
    items = []
    try:
        resp = requests.get(CAC_URL, timeout=30, headers={
            "User-Agent": "Mozilla/5.0 (compatible; SecurityBriefingBot/1.0)"
        })
        resp.encoding = "utf-8"
        soup = BeautifulSoup(resp.text, "html.parser")
    except Exception as e:
        print(f"  [X] 中国网信网: {e}")
        return items

    seen_urls = set()
    for a in soup.find_all("a", href=True):
        href = urllib.parse.urljoin("https://www.cac.gov.cn", a["href"].strip())
        text = a.get_text(strip=True)
        if not is_valid_cac_item(text, href):
            continue
        if not any(kw in text for kw in CAC_KEEP):
            continue
        if href in seen_urls:
            continue
        seen_urls.add(href)
        published = ""
        dm = re.search(r"/(\d{4}[-/]\d{2}[-/]\d{2})/", href)
        if not dm:
            continue
        published = dm.group(1).replace("/", "-")
        try:
            pub_date = datetime.strptime(published, "%Y-%m-%d")
            if (datetime.now() - pub_date).days > 7:
                continue
        except ValueError:
            continue
        items.append({
            "title": text,
            "url": href,
            "summary": "",
            "source": CAC_SOURCE,
            "published": published,
            "is_cn": True,
        })
    seen2 = {}
    for it in items:
        if it["url"] not in seen2:
            seen2[it["url"]] = it
    return list(seen2.values())

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

    print("\n  安全内参...")
    secrss = fetch_secrss()
    print(f"    安全内参: {len(secrss)}")
    all_items.extend(secrss)

    print("\n  NVD 漏洞...")
    nvd = fetch_nvd()
    print(f"    NVD: {len(nvd)}")
    all_items.extend(nvd)

    print("\n  中国网信网...")
    cac = fetch_cac()
    print(f"    中国网信网: {len(cac)}")
    all_items.extend(cac)

    seen = set()
    unique = []
    for it in all_items:
        key = hashlib.md5((it["title"] + it["source"]).encode("utf-8")).hexdigest()
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
