"""Website crawler.

Design choices:
- Async httpx with a global concurrency limit, so 500 leads finish in minutes.
- Only a handful of pages per company (home, about, services, contact, careers).
  The signals we need live there, and it keeps us polite.
- robots.txt is respected and a descriptive User-Agent is sent.
- Responses are cached in the database (PageCache) with a TTL.
- Retries with exponential backoff on 429/5xx and timeouts.
- CAPTCHA / bot-wall pages are detected and flagged, not bypassed.
- DEMO_MODE serves recorded pages from data/demo_sites.json so the demo
  works offline and is reproducible.
"""
import asyncio
import json
import os
import re
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from pathlib import Path
from urllib import robotparser
from urllib.parse import urljoin, urlparse

import httpx
from bs4 import BeautifulSoup

from .db import SessionLocal
from .models import PageCache

USER_AGENT = os.getenv(
    "CRAWLER_USER_AGENT",
    "DealSieveBot/1.0 (+https://github.com/your-username/dealsieve; lead research)",
)
MAX_HTML_BYTES = 1_500_000
CACHE_TTL = timedelta(hours=int(os.getenv("CACHE_TTL_HOURS", "72")))
DEMO_SITES_PATH = Path(__file__).resolve().parents[2] / "data" / "demo_sites.json"

LINK_HINTS = {
    "about": re.compile(r"about|our-story|history|who-we-are|our-team|meet", re.I),
    "services": re.compile(r"services?|what-we-do|solutions|plans|maintenance", re.I),
    "contact": re.compile(r"contact|locations?|get-in-touch", re.I),
    "careers": re.compile(r"careers?|jobs|join|hiring|employment", re.I),
}
BLOCK_TITLES = re.compile(r"just a moment|attention required|access denied|are you a robot|security check", re.I)


@dataclass
class FetchResult:
    url: str
    status: int
    html: str = ""
    final_url: str = ""
    blocked: bool = False
    error: str | None = None
    from_cache: bool = False

    @property
    def ok(self) -> bool:
        return 200 <= self.status < 300 and not self.blocked and bool(self.html)


def looks_blocked(status: int, html: str) -> bool:
    if status in (401, 403, 429) and re.search(r"captcha|cf-chl|challenge", html, re.I):
        return True
    title = re.search(r"<title[^>]*>(.*?)</title>", html, re.I | re.S)
    return bool(title and BLOCK_TITLES.search(title.group(1)))


def demo_mode() -> bool:
    return os.getenv("DEMO_MODE", "false").lower() in ("1", "true", "yes")


def load_demo_sites() -> dict:
    if DEMO_SITES_PATH.exists():
        return json.loads(DEMO_SITES_PATH.read_text())
    return {}


class Fetcher:
    def __init__(self, concurrency: int = 8, timeout: float = 12.0, demo_sites: dict | None = None):
        self.sem = asyncio.Semaphore(concurrency)
        self.demo_sites = demo_sites
        self._robots: dict[str, robotparser.RobotFileParser | None] = {}
        self.client = None
        if demo_sites is None:
            self.client = httpx.AsyncClient(
                timeout=timeout,
                follow_redirects=True,
                headers={"User-Agent": USER_AGENT, "Accept": "text/html,application/xhtml+xml"},
                limits=httpx.Limits(max_connections=concurrency * 2),
            )

    async def close(self):
        if self.client:
            await self.client.aclose()

    # ---- cache -------------------------------------------------------------
    def _cache_get(self, url: str) -> FetchResult | None:
        with SessionLocal() as db:
            row = db.get(PageCache, url)
            if not row:
                return None
            fetched = row.fetched_at if row.fetched_at.tzinfo else row.fetched_at.replace(tzinfo=timezone.utc)
            if datetime.now(timezone.utc) - fetched > CACHE_TTL:
                return None
            return FetchResult(url, row.status_code, row.html, row.final_url, bool(row.blocked), from_cache=True)

    def _cache_put(self, res: FetchResult):
        if res.status == 0:  # network errors are not cached
            return
        with SessionLocal() as db:
            db.merge(PageCache(url=res.url, status_code=res.status, final_url=res.final_url,
                               html=res.html, blocked=int(res.blocked),
                               fetched_at=datetime.now(timezone.utc)))
            db.commit()

    # ---- robots.txt ----------------------------------------------------------
    async def _allowed(self, url: str) -> bool:
        parsed = urlparse(url)
        origin = f"{parsed.scheme}://{parsed.netloc}"
        if origin not in self._robots:
            parser = None
            try:
                r = await self.client.get(origin + "/robots.txt", timeout=6)
                if r.status_code == 200:
                    parser = robotparser.RobotFileParser()
                    parser.parse(r.text.splitlines())
            except httpx.HTTPError:
                parser = None
            self._robots[origin] = parser
        parser = self._robots[origin]
        return parser is None or parser.can_fetch(USER_AGENT, url)

    # ---- fetch -------------------------------------------------------------
    async def fetch(self, url: str) -> FetchResult:
        if self.demo_sites is not None:
            return self._fetch_demo(url)

        cached = self._cache_get(url)
        if cached:
            return cached
        if not await self._allowed(url):
            return FetchResult(url, 0, error="Blocked by robots.txt")

        last_error = None
        for attempt in range(3):
            try:
                async with self.sem:
                    r = await self.client.get(url)
                if r.status_code in (429, 500, 502, 503, 504) and attempt < 2:
                    await asyncio.sleep(1.5 * (2 ** attempt))
                    continue
                ctype = r.headers.get("content-type", "")
                html = r.text[:MAX_HTML_BYTES] if "html" in ctype or not ctype else ""
                res = FetchResult(url, r.status_code, html, str(r.url), looks_blocked(r.status_code, html))
                self._cache_put(res)
                return res
            except httpx.TimeoutException:
                last_error = "Timed out"
            except httpx.HTTPError as exc:
                last_error = type(exc).__name__
                break  # DNS / connection errors won't fix themselves on retry
            await asyncio.sleep(1.0 * (attempt + 1))
        return FetchResult(url, 0, error=last_error or "Request failed")

    def _fetch_demo(self, url: str) -> FetchResult:
        parsed = urlparse(url)
        host = (parsed.hostname or "").removeprefix("www.")
        site = self.demo_sites.get(host)
        if site is None:
            return FetchResult(url, 0, error="Could not resolve host")
        path = parsed.path.rstrip("/") or "/"
        status = site.get("__status__", 200)
        html = site.get(path)
        if html is None:
            return FetchResult(url, 404, final_url=url)
        final = f"https://{host}{'' if path == '/' else path}"
        return FetchResult(url, status, html, final, looks_blocked(status, html))


def discover_links(html: str, base_url: str, domain: str) -> dict[str, str]:
    soup = BeautifulSoup(html, "html.parser")
    found: dict[str, str] = {}
    for a in soup.find_all("a", href=True):
        href = urljoin(base_url, a["href"])
        parsed = urlparse(href)
        if (parsed.hostname or "").removeprefix("www.") != domain or parsed.scheme not in ("http", "https"):
            continue
        haystack = f"{parsed.path} {a.get_text(' ', strip=True)}"
        for kind, pattern in LINK_HINTS.items():
            if kind not in found and pattern.search(haystack) and parsed.path not in ("", "/"):
                found[kind] = href.split("#")[0]
    return found


async def crawl_site(fetcher: Fetcher, domain: str) -> dict:
    home = None
    for base in (f"https://{domain}/", f"http://{domain}/"):
        home = await fetcher.fetch(base)
        if home.ok or home.blocked:
            break
    if not home.ok:
        return {
            "reachable": False,
            "blocked": home.blocked,
            "error": "Site shows a bot check (CAPTCHA). Review it manually." if home.blocked
            else (home.error or f"HTTP {home.status}"),
            "pages": {},
        }

    pages = {"home": {"url": home.final_url or home.url, "html": home.html}}
    for kind, url in discover_links(home.html, home.final_url or home.url, domain).items():
        res = await fetcher.fetch(url)
        if res.ok:
            pages[kind] = {"url": res.final_url or url, "html": res.html}
        if not res.from_cache and fetcher.demo_sites is None:
            await asyncio.sleep(0.4)  # be gentle with small-business servers

    return {
        "reachable": True,
        "blocked": False,
        "https": (home.final_url or home.url).startswith("https://"),
        "pages": pages,
    }
