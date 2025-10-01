#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Feed + X Short/Long Report Monitor (with Rate Limit & Backoff)
- 优先 RSS/Atom，其次 HTML 解析
- X (Twitter) recent search：账户定向 + 关键词
- 内建：速率限制、失败退避、配额保护（避免 429）

Usage:
  python monitor_feeds_and_x_rl.py --interval 10 --x on
  python monitor_feeds_and_x_rl.py --once --x on
"""

import argparse, json, os, re, sys, time, random
from datetime import datetime, timezone
from typing import List, Dict, Tuple, Optional
import requests
from bs4 import BeautifulSoup
import feedparser

STATE_FILE = "report_monitor_state.json"
HEADERS = {"User-Agent": "Mozilla/5.0 (ReportMonitor/2.1)"}
TIMEOUT = 25

DEFAULT_SITES = [
    "https://hindenburgresearch.com/",
   # "https://muddywatersresearch.com/research/",
    "https://citronresearch.com/",
  #  "https://www.kerrisdalecap.com/research/",
    "https://www.sprucepointcap.com/research/",
]
DEFAULT_X_ACCOUNTS = ["muddywatersre","HindenburgRes","CitronResearch","KerrisdaleCap","sprucepointcap"]
DEFAULT_X_KEYWORDS = [
    "short report","initiating short","short thesis","bearish report",
    "long report","initiating long","long thesis"
]

# ===================== 公共工具与退避 =====================

def now_iso() -> str:
    return datetime.now(timezone.utc).astimezone().isoformat(timespec="seconds")

def load_state() -> Dict:
    if not os.path.exists(STATE_FILE): return {}
    try:
        with open(STATE_FILE,"r",encoding="utf-8") as f: return json.load(f)
    except Exception:
        return {}

def save_state(state: Dict) -> None:
    tmp = STATE_FILE + ".tmp"
    with open(tmp,"w",encoding="utf-8") as f:
        json.dump(state,f,ensure_ascii=False,indent=2)
    os.replace(tmp,STATE_FILE)

def backoff_sleep(attempt:int, base:float=1.0, factor:float=2.0, cap:float=60.0, jitter:float=0.3):
    # 指数退避 + 抖动
    delay = min(base * (factor ** max(0,attempt-1)), cap)
    jitter_span = delay * jitter
    delay = max(0.0, delay + random.uniform(-jitter_span, jitter_span))
    time.sleep(delay)

def fetch_with_retry(url:str, headers=None, timeout:int=TIMEOUT, max_attempts:int=5) -> str:
    headers = headers or HEADERS
    attempt = 0
    while True:
        attempt += 1
        try:
            r = requests.get(url, headers=headers, timeout=timeout)
            if r.status_code == 429:
                reset = r.headers.get("Retry-After")
                wait_s = int(reset) if (reset and reset.isdigit()) else 30
                print(f"[{now_iso()}] INFO  | HTTP 429 for {url}, sleeping {wait_s}s…", flush=True)
                time.sleep(wait_s); continue
            if 500 <= r.status_code < 600:
                if attempt >= max_attempts:
                    r.raise_for_status()
                print(f"[{now_iso()}] WARN  | HTTP {r.status_code} {url}, retry {attempt}/{max_attempts}", flush=True)
                backoff_sleep(attempt); continue
            r.raise_for_status()
            return r.text
        except requests.RequestException as e:
            if attempt >= max_attempts:
                raise
            print(f"[{now_iso()}] WARN  | Fetch error {e} {url}, retry {attempt}/{max_attempts}", flush=True)
            backoff_sleep(attempt)

def absolute(url: str, base: str) -> str:
    if url.startswith("http"): return url
    if url.startswith("//"): return "https:" + url
    if url.startswith("/"):
        from urllib.parse import urlparse, urlunparse
        p = urlparse(base)
        return urlunparse((p.scheme, p.netloc, url, "", "", ""))
    from urllib.parse import urljoin
    return urljoin(base, url)

# ===================== Ticker/立场解析 =====================

TICKER_PATTERNS = [
    r"\$([A-Z]{1,5}(?:\.[A-Z]{1,2})?)",
    r"\b(?:NASDAQ|NYSE|AMEX|OTC|ASX):\s*([A-Z]{1,5}(?:\.[A-Z]{1,2})?)\b",
    r"\(([A-Z]{1,5}(?:\.[A-Z]{1,2})?)\)",
    r"\b([A-Z]{1,5}(?:\.[A-Z]{1,2})?)\b",
]
COMMON_WORDS = set("""
THE AND FOR WITH FROM THIS THAT HAVE HAS LONG SHORT REPORT RESEARCH UPDATE NEW
ON IN AT BY OUR WE ARE IS A AN OF TO AS NOTE INITIATING POSITION
BEARISH BULLISH SELL BUY INITIATED COVERAGE PRICE TARGET DOWNGRADE UPGRADE
""".split())

def extract_ticker(text: str) -> str:
    if not text: return ""
    for pat in TICKER_PATTERNS[:-1]:
        m = re.search(pat, text, re.IGNORECASE)
        if m: return m.group(1).upper()
    for c in re.findall(TICKER_PATTERNS[-1], text):
        up = c.upper()
        if 1 <= len(up) <= 5 and up.isalpha() and up not in COMMON_WORDS:
            return up
    return ""

def guess_stance(text: str) -> str:
    low = (text or "").lower()
    if any(k in low for k in ["initiating short","short report","short thesis","bear case","bearish","sell"]): return "short"
    if any(k in low for k in ["initiating long","long report","long thesis","bull case","bullish","buy"]): return "long"
    if "short" in low: return "short"
    if "long" in low: return "long"
    return "report"

def print_alert(source: str, title: str, url: str, stance: str, ticker: str):
    ts = now_iso(); tick = ticker or "UNKNOWN"
    print(f"[{ts}] ALERT | {source} | {stance.upper()} | {tick} | {title} | {url}", flush=True)

# ===================== 站点抓取 (RSS 优先 / HTML 退回) =====================

def discover_feeds(base_url: str) -> List[str]:
    feeds = []
    if base_url.endswith("/"): feeds.append(absolute("feed", base_url))
    try:
        html = fetch_with_retry(base_url)
        soup = BeautifulSoup(html, "lxml")
        for link in soup.find_all("link", rel=lambda x: x and "alternate" in x):
            typ = (link.get("type") or "").lower()
            if any(k in typ for k in ["rss","atom","xml"]):
                href = link.get("href")
                if href: feeds.append(absolute(href, base_url))
        if "wordpress" in html.lower() and base_url.endswith("/"):
            feeds.append(absolute("feed/", base_url))
    except Exception:
        pass
    uniq=[]; seen=set()
    for f in feeds:
        if f not in seen:
            seen.add(f); uniq.append(f)
    return uniq

def parse_feed(url: str) -> List[Tuple[str,str,str]]:
    out=[]; fp = feedparser.parse(url)
    for e in fp.entries[:20]:
        title = (e.get("title") or "").strip()
        link  = (e.get("link") or e.get("id") or "").strip()
        if title and link: out.append((title, link, guess_stance(title)))
    return out

def parse_html_default(base: str) -> List[Tuple[str,str,str]]:
    html = fetch_with_retry(base)
    soup = BeautifulSoup(html,"lxml")
    items=[]
    for a in soup.select("article a[href], .post a[href], a[href*='research'], a[href*='report']"):
        href = a.get("href","").strip()
        title = a.get_text(" ", strip=True)
        if not href: continue
        href = absolute(href, base)
        if not title: title = href
        items.append((title, href, guess_stance(title + " " + href)))
    seen=set(); out=[]
    for t,u,s in items:
        if u not in seen:
            seen.add(u); out.append((t,u,s))
    return out[:30]

def fetch_site_items(site_url: str) -> List[Tuple[str,str,str]]:
    feeds = discover_feeds(site_url)
    for f in feeds:
        try:
            items = parse_feed(f)
            if items: return items
        except Exception: pass
    try:
        return parse_html_default(site_url)
    except Exception:
        return []

# ===================== X API 客户端：配额保护 + 退避 =====================

class XQuota:
    """跟踪 recent search 限额；读取响应头；在低剩余时降级/休眠到 reset"""
    def __init__(self):
        self.remaining: Optional[int] = None
        self.limit: Optional[int] = None
        self.reset_ts: Optional[int] = None

    def update(self, headers: requests.structures.CaseInsensitiveDict):
        try:
            if "x-rate-limit-remaining" in headers:
                self.remaining = int(headers.get("x-rate-limit-remaining"))
            if "x-rate-limit-limit" in headers:
                self.limit = int(headers.get("x-rate-limit-limit"))
            if "x-rate-limit-reset" in headers:
                self.reset_ts = int(headers.get("x-rate-limit-reset"))
        except Exception:
            pass

    def time_to_reset(self) -> int:
        if not self.reset_ts: return 0
        return max(0, int(self.reset_ts - time.time()) + 1)

    def guard(self, soft_remaining:int) -> bool:
        """返回 True 表示需要暂停（剩余过低，建议等到 reset）"""
        return (self.remaining is not None and self.remaining <= soft_remaining)

class XHTTPClient:
    BASE = "https://api.x.com"
    def __init__(self, bearer: str, timeout:int=30):
        self.session = requests.Session()
        self.session.headers.update({"Authorization": f"Bearer {bearer}", "User-Agent": "ReportMonitor-X/2.1"})
        self.timeout = timeout
        self.quota = XQuota()

    def _get_json(self, path:str, params:dict, max_attempts:int=6):
        url = self.BASE + path
        attempt = 0
        while True:
            attempt += 1
            try:
                r = self.session.get(url, params=params, timeout=self.timeout)
                # 配额头更新（无论成功与否尽量记录）
                self.quota.update(r.headers)

                if r.status_code == 429:
                    wait_s = self.quota.time_to_reset() or 60
                    print(f"[{now_iso()}] INFO  | X 429 rate-limited. Sleeping {wait_s}s until reset…", flush=True)
                    time.sleep(wait_s)
                    attempt = 0
                    continue
                if 500 <= r.status_code < 600:
                    if attempt >= max_attempts: r.raise_for_status()
                    print(f"[{now_iso()}] WARN  | X {r.status_code}. Retry {attempt}/{max_attempts}", flush=True)
                    backoff_sleep(attempt); continue

                r.raise_for_status()
                return r.json(), r.headers
            except requests.RequestException as e:
                if attempt >= max_attempts: raise
                print(f"[{now_iso()}] WARN  | X request error {e}. Retry {attempt}/{max_attempts}", flush=True)
                backoff_sleep(attempt)

    def recent_search(self, query:str, max_results:int=20, lang:str="en"):
        params = {
            "query": query,
            "max_results": max(10, min(max_results, 100)),
            "tweet.fields": "created_at,lang,entities,author_id",
        }
        if lang: params["query"] += f" lang:{lang}"
        data, headers = self._get_json("/2/tweets/search/recent", params)
        tweets = (data or {}).get("data") or []
        return tweets, headers

# ===================== 监控流程 =====================

def build_x_queries(accounts: List[str], keywords: List[str]) -> Tuple[List[str], str]:
    kw = " OR ".join([f'"{k}"' for k in keywords])
    account_queries = [f"from:{acc} ({kw}) -is:retweet -is:reply" for acc in accounts]
    broad_query    = f"({kw}) (short OR report OR thesis) -is:retweet"
    return account_queries, broad_query

def extract_url_from_tweet(t: dict) -> str:
    ents = (t.get("entities") or {})
    urls = ents.get("urls") or []
    for u in urls:
        exp = u.get("expanded_url") or u.get("url")
        if exp: return exp
    return f"https://x.com/i/web/status/{t.get('id')}"

def scan_sites_once(state: Dict, sites: List[str]) -> None:
    for site in sites:
        try:
            items = fetch_site_items(site)
        except Exception as e:
            print(f"[{now_iso()}] WARN  | {site} | feed/html failed: {e}", file=sys.stderr, flush=True)
            continue
        seen = set(state.get(site, []))
        new_items = [(t,u,s) for (t,u,s) in items if u not in seen]
        for title, url, stance in new_items:
            ticker = extract_ticker(title)
            if not ticker:
                try:
                    body = fetch_with_retry(url)
                    soup = BeautifulSoup(body, "lxml")
                    main = " ".join(x.get_text(' ', strip=True) for x in soup.find_all(["h1","h2","p","li"]))
                    ticker = extract_ticker(main)
                except Exception:
                    pass
            print_alert(site, title, url, stance, ticker)
            state.setdefault(site, []).append(url)
        if site in state and len(state[site]) > 300:
            state[site] = state[site][-300:]

def scan_x_once(state: Dict, accounts: List[str], keywords: List[str],
                x_max_per_run:int=8, x_soft_remaining:int=100, degrade_broad:bool=True) -> None:
    bearer = os.getenv("X_BEARER_TOKEN","")
    if not bearer:
        print(f"[{now_iso()}] INFO  | X disabled (no X_BEARER_TOKEN).", flush=True)
        return

    client = XHTTPClient(bearer)
    acct_queries, broad_query = build_x_queries(accounts, keywords)

    # 轮询指针（跨轮延续，平滑用量）
    rr_key = "_x_rr_idx"
    rr_idx = int(state.get(rr_key, 0)) % max(1, len(acct_queries))

    # 组合本轮要跑的查询序列（先几个账户，再视配额决定是否跑广域）
    queries = []
    # 尽量把账户查询均摊到多轮
    for i in range(len(acct_queries)):
        q = acct_queries[(rr_idx + i) % len(acct_queries)]
        queries.append(("acct", q))
    # 广域关键词查询放最后，便于在低剩余时丢弃
    queries.append(("broad", broad_query))

    src_name = "X"
    seen = set(state.get(src_name, []))
    calls = 0

    for q_type, q in queries:
        if calls >= x_max_per_run:
            break

        # 软阈值保护：剩余过低时跳过广域或直接等待 reset
        if client.quota.guard(x_soft_remaining):
            if q_type == "broad" and degrade_broad:
                print(f"[{now_iso()}] INFO  | Skip broad query (remaining≤{x_soft_remaining}).", flush=True)
                continue
            # 如果连账户查询也扛不住，则休眠到 reset
            wait_s = client.quota.time_to_reset()
            if wait_s > 0:
                print(f"[{now_iso()}] INFO  | Remaining≤{x_soft_remaining}. Sleeping {wait_s}s until reset…", flush=True)
                time.sleep(wait_s)

        tweets, _hdr = client.recent_search(q, max_results=20, lang="en")
        calls += 1

        for t in tweets:
            url = extract_url_from_tweet(t)
            if url in seen: continue
            text = (t.get("text") or "").replace("\n"," ").strip()
            stance = guess_stance(text)
            ticker = extract_ticker(text)
            print_alert(src_name, text, url, stance, ticker)
            state.setdefault(src_name, []).append(url)
            seen.add(url)

        # 每做一次调用后，若剩余接近软阈值，主动 break，留配额给下轮
        if client.quota.guard(x_soft_remaining):
            print(f"[{now_iso()}] INFO  | Near quota floor. Stop X this round.", flush=True)
            break

    # 更新轮询指针并裁剪状态长度
    state[rr_key] = (rr_idx + calls) % max(1, len(acct_queries))
    if src_name in state and len(state[src_name]) > 600:
        state[src_name] = state[src_name][-600:]

# ===================== 主程序 =====================

def main():
    p = argparse.ArgumentParser(description="Monitor stock reports via Feeds + X with rate limits/backoff.")
    p.add_argument("--interval", type=int, default=10, choices=[10,30], help="Scan interval minutes.")
    p.add_argument("--once", action="store_true", help="Run one scan and exit.")
    p.add_argument("--sites", type=str, default="default", help='Comma-separated site URLs, or "default".')
    p.add_argument("--x", choices=["on","off"], default="off", help="Enable X (Twitter) monitoring.")
    p.add_argument("--x_accounts", type=str, default=",".join(DEFAULT_X_ACCOUNTS), help="Comma-separated X usernames.")
    p.add_argument("--x_keywords", type=str, default=",".join(DEFAULT_X_KEYWORDS), help="Comma-separated keywords/phrases.")
    p.add_argument("--x-max-per-run", type=int, default=8, help="Max X API calls per scan loop.")
    p.add_argument("--x-soft-remaining", type=int, default=3, help="Soft floor of remaining; below it we degrade/stop.")
    p.add_argument("--x-degrade-broad", choices=["yes","no"], default="yes", help="Skip broad query near quota floor.")
    args = p.parse_args()

    sites = DEFAULT_SITES if args.sites.strip().lower()=="default" else [s.strip() for s in args.sites.split(",") if s.strip()]
    x_on = (args.x == "on")
    x_accounts = [a.strip().lstrip("@") for a in args.x_accounts.split(",") if a.strip()]
    x_keywords = [k.strip() for k in args.x_keywords.split(",") if k.strip()]

    state = load_state()

    def run_once():
        scan_sites_once(state, sites)
        if x_on:
            scan_x_once(
                state, x_accounts, x_keywords,
                x_max_per_run=args.x_max_per_run,
                x_soft_remaining=args.x_soft_remaining,
                degrade_broad=(args.x_degrade_broad=="yes"),
            )
        save_state(state)

    if args.once:
        run_once(); return

    print(f"[{now_iso()}] INFO  | Monitor started. Interval: {args.interval}m | Sites: {len(sites)} | X: {'ON' if x_on else 'OFF'}", flush=True)
    while True:
        try:
            run_once()
        except KeyboardInterrupt:
            print(f"[{now_iso()}] INFO  | Stopped by user.", flush=True); break
        except Exception as e:
            print(f"[{now_iso()}] ERROR | Unexpected: {e}", file=sys.stderr, flush=True)
        time.sleep(args.interval * 60)

if __name__ == "__main__":
    main()
