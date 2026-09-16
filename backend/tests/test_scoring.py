import json
from datetime import date
from pathlib import Path

from app.extract import extract_signals
from app.scoring import score_lead

SITES = json.loads((Path(__file__).resolve().parents[2] / "data" / "demo_sites.json").read_text())
TODAY = date(2026, 9, 16)


def crawl(domain):
    site = SITES[domain]
    pages = {"home": {"url": f"https://{domain}/", "html": site["/"]}}
    for path, kind in [("/about", "about"), ("/services", "services"), ("/contact", "contact"), ("/careers", "careers")]:
        if path in site:
            pages[kind] = {"url": f"https://{domain}{path}", "html": site[path]}
    return {"reachable": True, "https": True, "pages": pages}


def test_extracts_core_signals():
    s = extract_signals(crawl("reyescomfort.test"), today=TODAY)
    assert s["founded_year"] == 1989
    assert s["owner_name"] == "Frank Reyes"
    assert s["family_owned"] and s["succession"]
    assert "maintenance plan" in s["recurring_terms"]
    assert "frank@reyescomfort.test" in s["emails"]
    assert s["tech"]["cms"] == "WordPress"
    assert s["evidence"]["founded_year"]["page"] == "home"


def test_ideal_target_scores_higher_than_pe_backed():
    good = score_lead({"industry": "HVAC", "employees": 42, "email_status": "valid", "domain": "x"},
                      extract_signals(crawl("reyescomfort.test"), today=TODAY), today=TODAY)
    pe = score_lead({"industry": "Commercial Cleaning", "employees": 120, "email_status": "role", "domain": "x"},
                    extract_signals(crawl("keystoneclean.test"), today=TODAY), today=TODAY)
    assert good["tier"] == "A"
    assert good["score"] > pe["score"] + 20
    assert any("investor" in f["text"] for f in pe["flags"])


def test_weights_change_the_score():
    signals = extract_signals(crawl("brightlineit.test"), today=TODAY)
    lead = {"industry": "IT Services", "employees": 60, "email_status": "role", "domain": "x"}
    base = score_lead(lead, signals, today=TODAY)["score"]
    no_upside = score_lead(lead, signals, {"weights": {"upside": 0}}, today=TODAY)["score"]
    assert no_upside > base  # Brightline is already digital, so removing that component helps it


def test_unreachable_site_has_low_confidence():
    result = score_lead({"domain": "gone.test"}, extract_signals({"reachable": False, "error": "DNS"}), today=TODAY)
    assert result["confidence"] < 50
    assert any("unreachable" in f["text"] for f in result["flags"])
