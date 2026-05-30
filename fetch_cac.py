#!/usr/bin/env python3
"""从中国网信网（cac.gov.cn）抓取网络安全相关政策法规"""
import json, os, re, sys
from datetime import datetime
from urllib.parse import urlparse

import requests
from bs4 import BeautifulSoup

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
RAW_FILE = os.path.join(BASE_DIR, "raw_data.json")
SOURCE_NAME = "中国网信网"

# 只保留政策/法规/安全相关的条目关键词
KEEP_KEYWORDS = [
    "网信", "安全", "网络", "数据", "信息", "法规", "规定", "办法",
    "通知", "意见", "指南", "标准", "监管", "治理", "合规",
    "清朗", "整治", "专项行动", "备案",
    "数字素养", "信息化", "人工智能", "算法", "互联网",
    "个人信息", "数据出境", "网络暴力", "网络谣言",
    "算法推荐", "深度合成", "生成式",
    "个人信息保护", "网络安全",
    "网络执法", "网络举报", "网络法治",
]

# 排除：导航链接、工具入口、外部链接、低价值地方新闻
SKIP_TITLES = [
    "设为首页", "加入收藏", "手机版",
    "主任信箱", "返回顶部", "学习强国",
    "相关链接", "联系我们",
    "纪检监察举报信箱",
    "互联网新闻信息稿源单位名单",
    "互联网新闻信息服务单位许可信息",
    "金融信息服务许可名单",
    "互联网信息服务算法备案系统",
    "区块链信息服务备案管理系统",
    "网络关键设备和网络安全专用产品安全认证",
    "政务应用程序规范化管理系统",
    "数据出境安全评估",
    "数据出境申报系统",
    "国家信息安全漏洞共享平台",
    "个人信息保护业务系统",
    "国家信息技术安全研究中心",
    "国家标准化管理委员会",
    "国家互联网信息办公室",
    "国家矿山安全监察局",
    "中国互联网联合辟谣平台",
    "国家新闻出版署", "国家宗教事务局",
    "国务院研究室", "国务院侨务办公室",
]

SKIP_PREFIXES = [
    "中央网信办所属", "中央网络安全和信息化委员会办公室关于",
    "世界互联网大会举行",
    "中国互联网发展基金会召开",
]

# 跳过地方网信办主任会议类
SKIP_LOCAL_REGEX = re.compile(r"(上海|天津|福建|江西|四川|广东|北京|浙江|江苏|河北|山东)\w*(网信办|委)")


def normalize_url(base_url, href):
    href = href.strip()
    if not href or href.startswith("#") or href.startswith("javascript:"):
        return None
    if href.startswith("//"):
        return "https:" + href
    if href.startswith("/"):
        return "https://www.cac.gov.cn" + href
    if not href.startswith("http"):
        from urllib.parse import urljoin
        return urljoin(base_url, href)
    return href


def is_valid_item(text, url):
    if len(text) < 8:
        return False
    for t in SKIP_TITLES:
        if t in text:
            return False
    for p in SKIP_PREFIXES:
        if text.startswith(p):
            return False
    if SKIP_LOCAL_REGEX.match(text):
        return False
    # 排除外部链接
    parsed = urlparse(url)
    if parsed.netloc and "cac.gov.cn" not in parsed.netloc:
        return False
    return True


def extract_items(soup, base_url):
    items = []
    seen_urls = set()
    for a in soup.find_all("a", href=True):
        href = normalize_url(base_url, a["href"])
        if not href:
            continue
        text = a.get_text(strip=True)
        if not is_valid_item(text, href):
            continue
        if not any(kw in text for kw in KEEP_KEYWORDS):
            continue
        if href in seen_urls:
            continue
        seen_urls.add(href)
        # 提取发布日期
        published = ""
        dm_url = re.search(r"/(\d{4}[-/]\d{2}[-/]\d{2})/", href)
        if dm_url:
            published = dm_url.group(1).replace("/", "-")
        else:
            parent = a.find_parent(["li", "div", "section", "dd", "dt", "ul"])
            if parent:
                dm = re.search(r"(\d{4}[-/]\d{1,2}[-/]\d{1,2})", parent.get_text())
                if dm:
                    published = dm.group(1).replace("/", "-")
        if not published:
            published = datetime.now().strftime("%Y-%m-%d")
        items.append({
            "title": text,
            "url": href,
            "summary": "",
            "source": SOURCE_NAME,
            "published": published,
            "is_cn": True,
        })
    seen2 = {}
    for it in items:
        if it["url"] not in seen2:
            seen2[it["url"]] = it
    return list(seen2.values())


def merge_to_raw(new_items):
    existing = []
    if os.path.exists(RAW_FILE):
        with open(RAW_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
            existing = data.get("items", [])
    existing_urls = {e["url"] for e in existing}
    added = 0
    for it in new_items:
        if it["url"] not in existing_urls:
            existing.append(it)
            existing_urls.add(it["url"])
            added += 1
    with open(RAW_FILE, "w", encoding="utf-8") as f:
        json.dump({
            "fetched_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "total": len(existing),
            "items": existing
        }, f, ensure_ascii=False, indent=2)
    print(f"  [OK] 新增 {added} 条，共 {len(existing)} 条")
    return added


def main():
    print("=" * 50)
    print(f"  [抓取] {SOURCE_NAME}")
    print(f"  {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 50)

    url = "https://www.cac.gov.cn/index.htm"
    try:
        resp = requests.get(url, timeout=30, headers={
            "User-Agent": "Mozilla/5.0 (compatible; SecurityBriefingBot/1.0)"
        })
        resp.encoding = "utf-8"
        soup = BeautifulSoup(resp.text, "html.parser")
    except Exception as e:
        print(f"  [X] 抓取失败: {e}")
        return

    items = extract_items(soup, url)
    print(f"  首页: {len(items)} 条")

    # 抓栏目页补充
    section_urls = [
        "https://www.cac.gov.cn/wxzw/wxfb/A093701index_1.htm",
        "https://www.cac.gov.cn/wxzw/zcfg/A093702index_1.htm",
        "https://www.cac.gov.cn/wxzw/wlaq/A093706index_1.htm",
        "https://www.cac.gov.cn/wxzw/sjzl/A093708index_1.htm",
    ]
    for surl in section_urls:
        try:
            r2 = requests.get(surl, timeout=30, headers={
                "User-Agent": "Mozilla/5.0 (compatible; SecurityBriefingBot/1.0)"
            })
            r2.encoding = "utf-8"
            s2 = BeautifulSoup(r2.text, "html.parser")
            sec_items = extract_items(s2, surl)
            items.extend(sec_items)
        except Exception:
            pass

    print(f"  总计: {len(items)} 条")

    if items:
        merge_to_raw(items)
    print("=" * 50)


if __name__ == "__main__":
    main()
