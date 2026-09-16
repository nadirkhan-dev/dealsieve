"""CSV import: flexible header mapping, normalization and de-duplication.

Accepts a SaaSquatch export or any CRM export. Column names are matched
against a list of aliases so users never have to rename headers by hand.
"""
import csv
import io
import re
from urllib.parse import urlparse

ALIASES: dict[str, list[str]] = {
    "name": ["company", "company name", "business name", "name", "organization", "account name", "business"],
    "website": ["website", "url", "domain", "company website", "web", "site", "company domain name", "website url"],
    "city": ["city", "town"],
    "state": ["state", "state/region", "region", "province"],
    "industry": ["industry", "category", "sector", "vertical"],
    "employees": ["employees", "employee count", "number of employees", "headcount", "company size", "size"],
    "revenue_estimate": ["revenue", "estimated revenue", "revenue estimate", "annual revenue"],
    "owner_name": ["owner", "owner name", "contact name", "full name", "ceo", "founder", "contact"],
    "email": ["email", "email address", "owner email", "contact email"],
    "phone": ["phone", "phone number", "telephone", "company phone"],
}

FREE_EMAIL_DOMAINS = {
    "gmail.com", "yahoo.com", "hotmail.com", "outlook.com", "aol.com", "icloud.com",
    "msn.com", "live.com", "comcast.net", "att.net", "sbcglobal.net", "verizon.net",
}

_LEGAL_SUFFIXES = r"\b(llc|l\.l\.c|inc|incorporated|co|corp|corporation|company|ltd|limited|pllc|pc|lp|the)\b"
_DOMAIN_RE = re.compile(r"^[a-z0-9](?:[a-z0-9-]{0,61}[a-z0-9])?(?:\.[a-z0-9-]{1,63})*\.[a-z]{2,24}$")

MAX_ROWS = 5000


def _header_key(header: str) -> str:
    return re.sub(r"[^a-z/ ]", "", header.strip().lower().replace("_", " ")).strip()


def map_headers(headers: list[str]) -> dict[str, str]:
    """Return {canonical_field: original_header}."""
    mapping: dict[str, str] = {}
    keys = {_header_key(h): h for h in headers}
    for field, aliases in ALIASES.items():
        for alias in aliases:
            if alias in keys and field not in mapping:
                mapping[field] = keys[alias]
                break
    return mapping


def normalize_domain(value: str | None) -> str | None:
    if not value:
        return None
    value = value.strip().lower()
    if "@" in value and "/" not in value:
        value = value.split("@", 1)[1]
    if not re.match(r"^[a-z]+://", value):
        value = "http://" + value
    host = urlparse(value).hostname or ""
    host = host.removeprefix("www.").strip(".")
    return host if _DOMAIN_RE.match(host) else None


def normalize_name(name: str) -> str:
    key = name.lower().replace("&", " and ")
    key = re.sub(_LEGAL_SUFFIXES, " ", key)
    key = re.sub(r"[^a-z0-9 ]", " ", key)
    return re.sub(r"\s+", " ", key).strip()


def parse_employees(value: str | None) -> int | None:
    if not value:
        return None
    nums = [int(n.replace(",", "")) for n in re.findall(r"\d[\d,]*", value)]
    if not nums:
        return None
    if len(nums) >= 2:  # a range like "11-50"
        return (nums[0] + nums[1]) // 2
    return nums[0]


def _clean(value: str | None) -> str | None:
    if value is None:
        return None
    value = re.sub(r"\s+", " ", value).strip()
    return value or None


def parse_csv(content: bytes) -> tuple[list[dict], dict]:
    text = content.decode("utf-8-sig", errors="replace")
    try:
        dialect = csv.Sniffer().sniff(text[:4096], delimiters=",;\t")
    except csv.Error:
        dialect = csv.excel
    reader = csv.DictReader(io.StringIO(text), dialect=dialect)
    headers = reader.fieldnames or []
    mapping = map_headers(headers)

    report = {
        "rows_read": 0,
        "unique_in_file": 0,
        "duplicates_in_file": 0,
        "skipped_missing_name": 0,
        "missing_website": 0,
        "mapped_columns": mapping,
        "unmapped_columns": [h for h in headers if h not in mapping.values()],
    }
    if "name" not in mapping:
        raise ValueError("Couldn't find a company name column. Add a column called 'Company' and try again.")

    seen: dict[str, dict] = {}
    for raw in reader:
        report["rows_read"] += 1
        if report["rows_read"] > MAX_ROWS:
            raise ValueError(f"This file has more than {MAX_ROWS} rows. Split it into smaller files.")
        row = {field: _clean(raw.get(header)) for field, header in mapping.items()}
        if not row.get("name"):
            report["skipped_missing_name"] += 1
            continue

        domain = normalize_domain(row.get("website"))
        email = (row.get("email") or "").lower() or None
        if not domain and email:
            email_domain = normalize_domain(email)
            if email_domain and email_domain not in FREE_EMAIL_DOMAINS:
                domain = email_domain

        lead = {
            "name": row["name"],
            "name_key": normalize_name(row["name"]),
            "domain": domain,
            "city": row.get("city"),
            "state": row.get("state"),
            "industry": row.get("industry"),
            "employees": parse_employees(row.get("employees")),
            "revenue_estimate": row.get("revenue_estimate"),
            "owner_name": row.get("owner_name"),
            "email": email,
            "phone": row.get("phone"),
        }
        if not domain:
            report["missing_website"] += 1

        key = domain or f"{lead['name_key']}|{(lead['city'] or '').lower()}"
        if key in seen:
            report["duplicates_in_file"] += 1
            existing = seen[key]
            for field, value in lead.items():  # merge: keep the most complete record
                if value and not existing.get(field):
                    existing[field] = value
        else:
            seen[key] = lead

    leads = list(seen.values())
    report["unique_in_file"] = len(leads)
    return leads, report
