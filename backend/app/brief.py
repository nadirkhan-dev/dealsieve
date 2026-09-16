"""Owner outreach brief.

Uses the Anthropic API when ANTHROPIC_API_KEY is set; otherwise falls back to
a deterministic template so the feature always works (and costs nothing in
the demo). The LLM only sees evidence we already extracted, which keeps it
grounded and avoids invented facts.
"""
import json
import os
import re

import httpx

ANTHROPIC_URL = "https://api.anthropic.com/v1/messages"
MODEL = os.getenv("LLM_MODEL", "claude-sonnet-4-6")


def _facts(lead: dict) -> dict:
    s = lead.get("signals") or {}
    return {
        "company": lead["name"],
        "location": ", ".join(x for x in [lead.get("city"), lead.get("state")] if x),
        "industry": lead.get("industry") or s.get("industry_guess"),
        "employees": lead.get("employees") or s.get("employees_hint"),
        "owner_name": lead.get("owner_name") or s.get("owner_name"),
        "years_in_business": s.get("years_in_business"),
        "description": s.get("description"),
        "recurring_revenue_offers": s.get("recurring_terms"),
        "family_owned": s.get("family_owned"),
        "succession_language": s.get("succession"),
        "digital_gaps": [b["reason"] for b in lead.get("breakdown", []) if b["key"] == "upside"],
        "score": lead.get("score"),
        "top_reasons": [b["reason"] for b in sorted(lead.get("breakdown", []), key=lambda b: -b["points"])[:3]],
        "risks": [f["text"] for f in lead.get("flags", []) if f["level"] != "good"],
    }


def template_brief(lead: dict) -> dict:
    f = _facts(lead)
    first = (f["owner_name"] or "").split()[0] if f["owner_name"] else "there"
    years = f["years_in_business"]
    tenure = f"{years} years" if years else "as long as you have"
    industry = (f["industry"] or "business").lower()

    why = list(f["top_reasons"])
    questions = [
        "What share of revenue comes from repeat customers or service agreements?",
        "How involved is the owner in day-to-day sales and scheduling?",
        "Is there a family member or key employee expected to take over?",
    ]
    if not f["recurring_revenue_offers"]:
        questions[0] = "Do customers come back on a schedule, or is most work one-off jobs?"

    body = (
        f"Hi {first},\n\n"
        f"I came across {f['company']} while researching {industry} companies"
        f"{' in ' + f['location'] if f['location'] else ''}. Building something that lasts "
        f"{tenure} is rare, and it's clear customers trust your team.\n\n"
        "I'm an operator looking to acquire and grow one great business for the long term, "
        "keeping the name, the team and the way you treat customers. If you've ever thought about "
        "what the next chapter looks like, I'd value a 15-minute conversation. No pressure and no "
        "brokers involved.\n\n"
        "Would a short call next week work?\n\nBest,\n[Your name]"
    )
    return {
        "source": "template",
        "summary": f"{f['company']} is a {industry} company"
                   f"{' in ' + f['location'] if f['location'] else ''}"
                   f"{f' operating for about {years} years' if years else ''}. "
                   f"Fit score {f['score']}/100.",
        "why_it_fits": why,
        "risks": f["risks"] or ["No major risks found in public information"],
        "questions": questions,
        "email_subject": f"Question about the future of {f['company']}",
        "email_body": body,
    }


async def generate_brief(lead: dict) -> dict:
    key = os.getenv("ANTHROPIC_API_KEY")
    if not key:
        return template_brief(lead)

    prompt = (
        "You help a search-fund entrepreneur prepare to contact the owner of a small business "
        "they may want to acquire. Use ONLY the facts below. Do not invent numbers or history.\n\n"
        f"FACTS:\n{json.dumps(_facts(lead), indent=2)}\n\n"
        "Return only JSON with keys: summary (2 sentences), why_it_fits (3 short strings), "
        "risks (1-3 short strings), questions (3 discovery questions for the first call), "
        "email_subject, email_body (under 130 words, warm, respectful of the owner's legacy, "
        "no hype, no mention of AI or scores, signed '[Your name]')."
    )
    try:
        async with httpx.AsyncClient(timeout=40) as client:
            r = await client.post(
                ANTHROPIC_URL,
                headers={"x-api-key": key, "anthropic-version": "2023-06-01", "content-type": "application/json"},
                json={"model": MODEL, "max_tokens": 1000, "messages": [{"role": "user", "content": prompt}]},
            )
            r.raise_for_status()
            text = "".join(b.get("text", "") for b in r.json().get("content", []))
            text = re.sub(r"^```(?:json)?|```$", "", text.strip(), flags=re.M).strip()
            data = json.loads(text)
            required = {"summary", "why_it_fits", "risks", "questions", "email_subject", "email_body"}
            if not required.issubset(data):
                raise ValueError("missing keys")
            data["source"] = "ai"
            return data
    except Exception:
        fallback = template_brief(lead)
        fallback["source"] = "template (AI unavailable)"
        return fallback
