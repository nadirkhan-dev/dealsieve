"""Turn crawled pages into acquisition signals.

Every signal keeps an evidence snippet and the page it came from, so a user
can see *why* the tool believes something instead of trusting a black box.
"""
import re
from datetime import date

from bs4 import BeautifulSoup

PAGE_ORDER = ["home", "about", "services", "contact", "careers"]

# Franchise wording. The first four are explicit; the rest are weaker hints that
# national franchise networks use on their location pages.
FRANCHISE_PHRASES = (
    r"independently owned and operated franchise|franchise location|a franchise of|franchisee"
    r"|locally owned and operated|independently owned and operated"
    r"|find a location near you|find your local"
    r"|franchise opportunities|own a franchise|become a franchisee"
)

# Well-known national service-franchise brands, matched against the company name
# and the home page <title>. These sites often never use the word "franchise" on
# the pages we crawl -- a real run missed Roto-Rooter exactly that way.
FRANCHISE_BRANDS = [
    "roto-rooter", "roto rooter", "mr. rooter", "mr rooter", "benjamin franklin plumbing",
    "one hour heating", "one hour air", "aire serv", "terminix", "servicemaster",
    "servpro", "molly maid", "merry maids", "the maids", "mosquito joe", "trugreen",
    "lawn doctor", "weed man", "chem-dry", "stanley steemer", "jan-pro", "jani-king",
    "anago", "mr. electric", "mr electric", "mr. handyman", "mr handyman",
    "glass doctor", "rainbow international", "ace handyman", "certapro",
    "five star painting", "budget blinds", "bath fitter", "precision garage door",
    "two men and a truck", "college hunks hauling junk", "1-800-got-junk", "junk king",
    "the cleaning authority", "pillar to post", "dryer vent wizard", "kitchen tune-up",
]


def match_franchise_brand(*haystacks) -> str | None:
    """Return the first known franchise brand found in any haystack, else None."""
    hay = " ".join(h.lower() for h in haystacks if h)
    return next((b for b in FRANCHISE_BRANDS if b in hay), None)


KEYWORDS = {
    "succession": r"retir(?:e|ing|ement)|succession|next chapter|business (?:is )?for sale|looking for (?:a|the right) (?:buyer|successor)|pass(?:ing)? the torch",
    "family_owned": r"family[- ]owned|family business|family[- ]run|second[- ]generation|third[- ]generation|father and son|mother and daughter",
    "hiring": r"we'?re hiring|now hiring|join our team|open positions|career opportunities",
    "franchise": FRANCHISE_PHRASES,
    "pe_backed": r"portfolio company|backed by .{0,40}(?:capital|partners|equity)|acquired by|a subsidiary of|part of the .{0,30} family of companies",
    "testimonials": r"testimonials?|what our customers say|reviews?|5[- ]star",
}
RECURRING_TERMS = r"maintenance (?:plan|agreement|program|membership)s?|service (?:agreement|contract|plan)s?|membership|subscription|monthly (?:plan|service)|annual (?:service|contract|inspection)s?|recurring|retainer|managed services"

INDUSTRY_KEYWORDS = {
    "HVAC": r"hvac|heating|air condition|furnace",
    "Plumbing": r"plumb|drain|water heater",
    "Electrical": r"electrician|electrical contractor",
    "Roofing": r"roofing|roofer",
    "Landscaping": r"landscap|lawn care",
    "Pest control": r"pest control|exterminat|termite",
    "Commercial cleaning": r"janitorial|commercial cleaning",
    "Accounting": r"accounting|bookkeeping|cpa firm|tax preparation",
    "IT services": r"managed it|it support|managed services provider|cybersecurity",
    "Manufacturing": r"manufactur|machining|fabrication|cnc",
    "Logistics": r"freight|trucking|logistics|warehous",
    "Dental": r"dental|dentist",
    "Auto repair": r"auto repair|collision|mechanic",
    "Marketing agency": r"marketing agency|digital marketing|seo services",
}

EMAIL_RE = re.compile(r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,24}")
PHONE_RE = re.compile(r"(?:\+?1[\s.-]?)?\(?([2-9]\d{2})\)?[\s.-]?(\d{3})[\s.-](\d{4})\b")
IGNORED_EMAIL_HOSTS = ("sentry.io", "wixpress.com", "example.com", "domain.com", "email.com", "yourdomain.com")
NAME_STOPWORDS = {"Our", "The", "Contact", "About", "Call", "Read", "Meet", "Learn", "Home", "Service",
                  "Services", "Get", "Free", "Request", "Book", "Customer", "Company", "Business"}
ROLE_WORDS = r"(?i:owner|founder|co-founder|president|ceo|proprietor)"


def _snippet(text: str, start: int, end: int, pad: int = 70) -> str:
    s, e = max(0, start - pad), min(len(text), end + pad)
    if s > 0:  # snap to whole words so quotes never start mid-word
        space = text.find(" ", s)
        s = space + 1 if 0 <= space < start else s
    if e < len(text):
        space = text.rfind(" ", end, e)
        e = space if space > end else e
    return ("…" if s > 0 else "") + text[s:e].strip() + ("…" if e < len(text) else "")


def _page_texts(pages: dict) -> list[tuple[str, str, str, str]]:
    """Return [(kind, url, visible_text, raw_html)] in a stable order."""
    out = []
    for kind in sorted(pages, key=lambda k: PAGE_ORDER.index(k) if k in PAGE_ORDER else 99):
        html = pages[kind]["html"]
        soup = BeautifulSoup(html, "html.parser")
        for tag in soup(["script", "style", "noscript", "svg"]):
            tag.decompose()
        text = re.sub(r"\s+", " ", soup.get_text(" ")).strip()
        out.append((kind, pages[kind]["url"], text, html))
    return out


def _search(texts, pattern, flags=re.I):
    for kind, _url, text, _html in texts:
        m = re.search(pattern, text, flags)
        if m:
            return m, {"page": kind, "text": _snippet(text, m.start(), m.end())}
    return None, None


def extract_signals(crawl: dict, today: date | None = None, company_name: str | None = None) -> dict:
    today = today or date.today()
    signals: dict = {
        "reachable": crawl.get("reachable", False),
        "blocked": crawl.get("blocked", False),
        "crawl_error": crawl.get("error"),
        "pages_crawled": sorted(crawl.get("pages", {}).keys()),
        "evidence": {},
    }
    # A known franchise brand in the company name needs no crawled page, so this
    # runs before the unreachable check.
    brand = match_franchise_brand(company_name)
    if brand:
        signals["franchise"] = True
        signals["evidence"]["franchise"] = {
            "page": "company name",
            "text": f"\u201c{company_name}\u201d matches the national franchise brand \u201c{brand}\u201d.",
        }

    if not signals["reachable"]:
        return signals

    texts = _page_texts(crawl["pages"])
    evidence = signals["evidence"]
    all_html = "\n".join(t[3] for t in texts)
    home_html = texts[0][3]
    home_soup = BeautifulSoup(home_html, "html.parser")

    if not signals.get("franchise"):
        title = home_soup.title.get_text(" ", strip=True) if home_soup.title else None
        brand = match_franchise_brand(title)
        if brand:
            signals["franchise"] = True
            evidence["franchise"] = {
                "page": "home",
                "text": f"Page title \u201c{title[:120]}\u201d matches the national franchise brand \u201c{brand}\u201d.",
            }

    # ---- founding year ---------------------------------------------------------
    years = []
    for kind, _url, text, _ in texts:
        for m in re.finditer(r"\b(?:since|founded(?: in)?|established(?: in)?|est\.?|in business since|opened (?:our doors )?in)\s+(1[89]\d{2}|20[0-2]\d)\b", text, re.I):
            y = int(m.group(1))
            if 1850 <= y <= today.year:
                years.append((y, {"page": kind, "text": _snippet(text, m.start(), m.end())}))
        for m in re.finditer(r"\b(?:for|over|more than|nearly|almost)\s+(\d{1,3})\+?\s+years\b", text, re.I):
            n = int(m.group(1))
            if 3 <= n <= 150:
                years.append((today.year - n, {"page": kind, "text": _snippet(text, m.start(), m.end())}))
    if years:
        founded, ev = min(years, key=lambda x: x[0])
        signals["founded_year"] = founded
        signals["years_in_business"] = today.year - founded
        evidence["founded_year"] = ev

    # ---- website freshness ----------------------------------------------------
    copy_years = [int(y) for y in re.findall(r"(?:©|&copy;|copyright)\s*(?:\d{4}\s*[-–]\s*)?(\d{4})", all_html, re.I)
                  if 1995 <= int(y) <= today.year]
    if copy_years:
        signals["copyright_year"] = max(copy_years)

    # ---- people ------------------------------------------------------------------
    name = r"([A-Z][a-z]+(?:\s[A-Z]\.)?\s[A-Z][a-zA-Z'\-]{1,20})"
    owner_patterns = [
        name + r",?\s+(?:is\s+)?(?:the\s+)?(?:(?i:our)\s+)?" + ROLE_WORDS + r"\b",
        ROLE_WORDS + r"\s*(?:[,:\-–]|and)?\s+" + name,
    ]
    for kind, _url, text, _ in texts:
        hit = None
        for pat in owner_patterns:
            for m in re.finditer(pat, text):
                candidate = m.group(1)
                if candidate.split()[0] not in NAME_STOPWORDS:
                    hit = (candidate, m)
                    break
            if hit:
                break
        if hit:
            signals["owner_name"] = hit[0]
            evidence["owner_name"] = {"page": kind, "text": _snippet(text, hit[1].start(), hit[1].end())}
            break

    # ---- keyword signals -------------------------------------------------------
    for key, pattern in KEYWORDS.items():
        m, ev = _search(texts, pattern)
        signals[key] = bool(m) or bool(signals.get(key))  # keep an earlier brand match
        if ev and key not in evidence:  # brand evidence is stronger, so it wins
            evidence[key] = ev

    recurring = []
    for kind, _url, text, _ in texts:
        for m in re.finditer(RECURRING_TERMS, text, re.I):
            term = m.group(0).lower()
            if term not in recurring:
                recurring.append(term)
                evidence.setdefault("recurring_revenue", {"page": kind, "text": _snippet(text, m.start(), m.end())})
    signals["recurring_terms"] = recurring[:6]

    emp = re.search(r"\b(?:team of|staff of|over|more than|nearly)\s+(\d{1,4})\s+(?:employees|technicians|team members|professionals|staff|people)\b",
                    " ".join(t[2] for t in texts), re.I)
    if emp:
        signals["employees_hint"] = int(emp.group(1))

    # ---- contact data ------------------------------------------------------------
    emails = []
    for m in EMAIL_RE.finditer(all_html):
        e = m.group(0).lower().strip(".")
        if e.endswith((".png", ".jpg", ".gif", ".webp", ".svg")) or e.split("@")[1] in IGNORED_EMAIL_HOSTS:
            continue
        if e not in emails:
            emails.append(e)
    signals["emails"] = emails[:8]

    phones = []
    for _kind, _url, text, _ in texts:
        for m in PHONE_RE.finditer(text):
            p = f"({m.group(1)}) {m.group(2)}-{m.group(3)}"
            if p not in phones:
                phones.append(p)
    signals["phones"] = phones[:4]

    socials = {}
    for a in home_soup.find_all("a", href=True):
        for net in ("linkedin", "facebook", "instagram"):
            if f"{net}.com" in a["href"] and net not in socials:
                socials[net] = a["href"]
    signals["socials"] = socials

    # ---- digital maturity (low maturity = post-acquisition upside) -----------
    lowered = all_html.lower()
    tech = {
        "cms": next((n for n, marker in [("WordPress", "wp-content"), ("Wix", "wixstatic"), ("Squarespace", "squarespace"),
                                         ("Shopify", "cdn.shopify"), ("GoDaddy Builder", "wsimg.com"), ("Weebly", "weebly")]
                     if marker in lowered), None),
        "https": bool(crawl.get("https")),
        "mobile_friendly": bool(home_soup.find("meta", attrs={"name": "viewport"})),
        "online_booking": bool(re.search(r"calendly|servicetitan|housecallpro|acuityscheduling|book online|schedule online", lowered)),
        "live_chat": bool(re.search(r"intercom|drift\.com|tawk\.to|livechatinc|podium", lowered)),
        "analytics": bool(re.search(r"googletagmanager|google-analytics|gtag\(", lowered)),
        "marketing_automation": bool(re.search(r"hs-scripts|mailchimp|klaviyo|activecampaign", lowered)),
    }
    fresh = bool(signals.get("copyright_year") and signals["copyright_year"] >= today.year - 1)
    maturity = (15 * tech["https"] + 20 * tech["mobile_friendly"] + 20 * fresh + 15 * tech["online_booking"]
                + 10 * tech["live_chat"] + 10 * tech["analytics"] + 10 * tech["marketing_automation"])
    signals["tech"] = tech
    signals["digital_maturity"] = maturity

    # ---- description & industry --------------------------------------------------
    meta = home_soup.find("meta", attrs={"name": "description"}) or home_soup.find("meta", attrs={"property": "og:description"})
    desc = (meta.get("content") if meta else None) or texts[0][2][:220]
    signals["description"] = desc.strip()[:300]

    corpus = " ".join(t[2] for t in texts[:3]).lower()
    counts = {ind: len(re.findall(p, corpus)) for ind, p in INDUSTRY_KEYWORDS.items()}
    best = max(counts, key=counts.get)
    signals["industry_guess"] = best if counts[best] >= 2 else None

    return signals
