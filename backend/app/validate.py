"""Contact validation: syntax, role-based detection, domain match and MX lookup.

We deliberately do NOT do SMTP "ping" verification: it is unreliable, can get
the sender's IP blacklisted, and many providers treat it as abuse.
"""
import re
from functools import lru_cache

from .ingest import FREE_EMAIL_DOMAINS

EMAIL_SYNTAX = re.compile(r"^[a-z0-9._%+-]+@[a-z0-9-]+(?:\.[a-z0-9-]+)*\.[a-z]{2,24}$")
ROLE_PREFIXES = {"info", "contact", "office", "admin", "sales", "support", "hello", "service", "team",
                 "help", "billing", "careers", "jobs", "hr", "marketing", "noreply", "no-reply", "webmaster",
                 "dispatch", "orders", "accounts", "reception", "estimates", "quotes"}


@lru_cache(maxsize=4096)
def has_mx(domain: str) -> bool | None:
    """True/False if we could check, None if DNS lookup is unavailable."""
    try:
        import dns.resolver  # dnspython

        answers = dns.resolver.resolve(domain, "MX", lifetime=3.0)
        return len(answers) > 0
    except ImportError:
        return None
    except Exception as exc:  # NXDOMAIN, NoAnswer, Timeout
        name = type(exc).__name__
        if name in ("NXDOMAIN", "NoAnswer", "NoNameservers"):
            return False
        return None


def classify_email(email: str | None, company_domain: str | None, mx_lookup=has_mx) -> str | None:
    """Return one of: valid, role, personal_domain, invalid, unverified (or None if no email)."""
    if not email:
        return None
    email = email.strip().lower()
    if not EMAIL_SYNTAX.match(email):
        return "invalid"
    local, host = email.split("@", 1)
    mx = mx_lookup(host)
    if mx is False:
        return "invalid"
    if local in ROLE_PREFIXES:
        return "role"
    if host in FREE_EMAIL_DOMAINS:
        return "personal_domain"
    if mx is None:
        return "unverified"
    return "valid"


def pick_best_email(candidates: list[str], owner_name: str | None, company_domain: str | None) -> str | None:
    """Prefer the owner's address, then any named address at the company domain, then a role inbox."""
    if not candidates:
        return None
    first = (owner_name or "").split()[0].lower() if owner_name else ""

    def rank(e: str) -> int:
        local, host = e.split("@", 1)
        on_domain = company_domain and host.endswith(company_domain)
        if first and first in local:
            return 0
        if on_domain and local not in ROLE_PREFIXES:
            return 1
        if on_domain:
            return 2
        return 3

    return sorted(candidates, key=rank)[0]


def normalize_phone(phone: str | None) -> str | None:
    if not phone:
        return None
    digits = re.sub(r"\D", "", phone)
    if len(digits) == 11 and digits.startswith("1"):
        digits = digits[1:]
    if len(digits) != 10:
        return phone.strip()
    return f"({digits[:3]}) {digits[3:6]}-{digits[6:]}"
