"""Acquisition Fit Score (0-100).

A transparent, rules-based model. Each component produces a 0-1 ratio and a
plain-English reason; the ratio is multiplied by a user-adjustable weight.

Why rules instead of an LLM for the score itself:
- Deterministic: the same lead always gets the same score.
- Explainable: every point can be traced to evidence on the website.
- Fast and free: rescoring 5,000 leads after an ICP change takes milliseconds.
The LLM is used where it is strongest: writing the outreach brief.
"""
from datetime import date

DEFAULT_ICP = {
    "target_industries": [
        "HVAC", "Plumbing", "Electrical", "Roofing", "Landscaping", "Pest control",
        "Commercial cleaning", "Accounting", "IT services", "Manufacturing", "Logistics",
    ],
    "employees_min": 5,
    "employees_max": 150,
    "min_years": 10,
    "weights": {
        "maturity": 20,
        "size": 15,
        "industry": 15,
        "recurring": 15,
        "succession": 15,
        "upside": 10,
        "reachability": 10,
    },
}

COMPONENT_LABELS = {
    "maturity": "Years in business",
    "size": "Company size",
    "industry": "Industry fit",
    "recurring": "Recurring revenue",
    "succession": "Owner transition",
    "upside": "Digital upside",
    "reachability": "Owner reachable",
}


def _industry_match(industry: str | None, targets: list[str]) -> bool:
    if not industry:
        return False
    ind = industry.lower()
    return any(t.lower() in ind or ind in t.lower() for t in targets)


def score_lead(lead: dict, signals: dict, icp: dict | None = None, today: date | None = None) -> dict:
    icp = {**DEFAULT_ICP, **(icp or {})}
    weights = {**DEFAULT_ICP["weights"], **icp.get("weights", {})}
    today = today or date.today()
    reachable = signals.get("reachable", False)
    years = signals.get("years_in_business")
    parts: dict[str, tuple[float, str, bool]] = {}  # key -> (ratio, reason, known)

    # Years in business: long-running businesses have proven, durable cash flow.
    min_years = icp["min_years"]
    if years is None:
        parts["maturity"] = (0.3, "Founding year not found on the website", False)
    elif years >= 2 * min_years:
        parts["maturity"] = (1.0, f"In business about {years} years", True)
    elif years >= min_years:
        parts["maturity"] = (0.75, f"In business about {years} years", True)
    elif years >= min_years / 2:
        parts["maturity"] = (0.4, f"Only about {years} years old", True)
    else:
        parts["maturity"] = (0.1, f"Young business (about {years} years)", True)

    # Size: small enough to be owner-operated, big enough to run without the owner.
    emp = lead.get("employees") or signals.get("employees_hint")
    lo, hi = icp["employees_min"], icp["employees_max"]
    if emp is None:
        parts["size"] = (0.35, "Headcount unknown", False)
    elif lo <= emp <= hi:
        parts["size"] = (1.0, f"About {emp} employees, inside your {lo}–{hi} range", True)
    elif lo * 0.5 <= emp <= hi * 1.5:
        parts["size"] = (0.5, f"About {emp} employees, just outside your {lo}–{hi} range", True)
    else:
        parts["size"] = (0.0, f"About {emp} employees, outside your {lo}–{hi} range", True)

    # Industry
    industry = lead.get("industry") or signals.get("industry_guess")
    if not industry:
        parts["industry"] = (0.35, "Industry unknown", False)
    elif _industry_match(industry, icp["target_industries"]):
        parts["industry"] = (1.0, f"{industry} is a target industry", True)
    else:
        parts["industry"] = (0.15, f"{industry} is not in your target list", True)

    # Recurring revenue: the strongest predictor of valuation for small businesses.
    terms = signals.get("recurring_terms") or []
    if not reachable:
        parts["recurring"] = (0.2, "Website not reviewed", False)
    elif len(terms) >= 2:
        parts["recurring"] = (1.0, "Recurring revenue offers: " + ", ".join(terms[:3]), True)
    elif len(terms) == 1:
        parts["recurring"] = (0.6, f"Mentions {terms[0]}", True)
    else:
        parts["recurring"] = (0.0, "No maintenance plans or contracts mentioned", True)

    # Owner transition: the reason an owner would take the call.
    if not reachable:
        parts["succession"] = (0.2, "Website not reviewed", False)
    elif signals.get("succession"):
        parts["succession"] = (1.0, "Website mentions retirement or succession", True)
    elif signals.get("family_owned") and (years or 0) >= 25:
        parts["succession"] = (0.7, "Long-running family business, likely thinking about the next generation", True)
    elif signals.get("owner_name") and (years or 0) >= 20:
        parts["succession"] = (0.5, f"Founder-led for {years}+ years", True)
    elif (years or 0) >= 30:
        parts["succession"] = (0.4, "30+ years old, owner likely nearing transition age", True)
    else:
        parts["succession"] = (0.0, "No transition signals found", True)

    # Digital upside: a dated web presence means room for post-acquisition value creation.
    if not reachable:
        parts["upside"] = (0.0, "Website not reviewed", False)
    else:
        maturity = signals.get("digital_maturity", 50)
        ratio = max(0.1, min(1.0, (100 - maturity) / 70))
        gaps = []
        tech = signals.get("tech", {})
        cy = signals.get("copyright_year")
        if cy and cy <= today.year - 3:
            gaps.append(f"site last updated around {cy}")
        if not tech.get("online_booking"):
            gaps.append("no online booking")
        if not tech.get("mobile_friendly"):
            gaps.append("not mobile friendly")
        if not tech.get("https"):
            gaps.append("no HTTPS")
        reason = ("Room to modernize: " + ", ".join(gaps[:3])) if gaps and ratio >= 0.5 else "Already digitally mature"
        parts["upside"] = (ratio, reason, True)

    # Reachability: can we get the owner on the phone?
    email_status = lead.get("email_status")
    r, bits = 0.0, []
    if email_status in ("valid", "personal_domain"):
        r += 0.5
        bits.append("direct email")
    elif email_status in ("role", "unverified"):
        r += 0.25
        bits.append("general inbox")
    if lead.get("phone") or signals.get("phones"):
        r += 0.3
        bits.append("phone")
    if lead.get("owner_name") or signals.get("owner_name"):
        r += 0.2
        bits.append("owner name")
    parts["reachability"] = (min(r, 1.0), ("Have " + ", ".join(bits)) if bits else "No contact details found", True)

    # ---- combine ----------------------------------------------------------------
    total_weight = sum(weights.values()) or 1
    breakdown, raw = [], 0.0
    for key, (ratio, reason, known) in parts.items():
        w = weights.get(key, 0)
        points = ratio * w
        raw += points
        breakdown.append({
            "key": key, "label": COMPONENT_LABELS[key], "points": round(points * 100 / total_weight, 1),
            "max": round(w * 100 / total_weight, 1), "ratio": round(ratio, 2), "reason": reason, "known": known,
        })
    score = raw * 100 / total_weight

    flags = []
    if signals.get("pe_backed"):
        score -= 25
        flags.append({"level": "risk", "text": "Appears to already be owned by an investor or parent company"})
    if signals.get("franchise"):
        score -= 15
        flags.append({"level": "risk", "text": "Franchise location, usually needs franchisor approval to sell"})
    if signals.get("blocked"):
        flags.append({"level": "watch", "text": "Website shows a bot check. Review it manually."})
    elif not reachable and lead.get("domain"):
        flags.append({"level": "watch", "text": f"Website unreachable ({signals.get('crawl_error') or 'no response'})"})
    if not lead.get("domain"):
        flags.append({"level": "watch", "text": "No website on record"})
    if email_status == "invalid":
        flags.append({"level": "watch", "text": "Email address looks invalid"})
    if signals.get("hiring"):
        flags.append({"level": "good", "text": "Currently hiring, a sign of demand"})

    score = int(round(max(0, min(100, score))))
    known = sum(1 for _, _, k in parts.values() if k)
    confidence = int(round(known / len(parts) * 100))
    tier = "A" if score >= 72 else "B" if score >= 55 else "C" if score >= 38 else "D"

    return {"score": score, "tier": tier, "confidence": confidence, "breakdown": breakdown, "flags": flags}
