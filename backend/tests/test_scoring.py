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


# ---- franchise detection ---------------------------------------------------
# A real run against live sites flagged Terminix and ServiceMaster but missed
# Roto-Rooter, whose crawled pages never use the word "franchise".

def test_franchise_brand_matched_from_company_name():
    s = extract_signals(crawl("reyescomfort.test"), today=TODAY,
                        company_name="Roto-Rooter Plumbing & Water Cleanup")
    assert s["franchise"] is True
    assert "roto-rooter" in s["evidence"]["franchise"]["text"].lower()
    assert s["evidence"]["franchise"]["page"] == "company name"


def test_franchise_brand_matched_even_when_site_unreachable():
    s = extract_signals({"reachable": False, "error": "HTTP 403", "pages": {}},
                        today=TODAY, company_name="TruGreen")
    assert s["franchise"] is True


def test_franchise_phrase_still_detected_without_a_known_brand():
    s = extract_signals(crawl("harborpointpest.test"), today=TODAY,
                        company_name="Harbor Point Pest Control")
    assert s["franchise"] is True


def test_independent_business_is_not_flagged_as_a_franchise():
    s = extract_signals(crawl("reyescomfort.test"), today=TODAY,
                        company_name="Reyes Comfort Heating & Air")
    assert s["franchise"] is False
    assert "franchise" not in s["evidence"]


def test_franchise_costs_the_lead_points():
    kwargs = dict(today=TODAY)
    lead = {"domain": "reyescomfort.test", "name": "Reyes Comfort Heating & Air"}
    clean = score_lead(lead, extract_signals(crawl("reyescomfort.test"), **kwargs), **kwargs)
    flagged = score_lead(lead, extract_signals(crawl("reyescomfort.test"), company_name="Molly Maid", **kwargs), **kwargs)
    assert flagged["score"] < clean["score"]
    assert any("franchise" in f["text"].lower() for f in flagged["flags"])


def test_competitor_mentioned_in_page_text_is_not_a_franchise():
    """Brand matching reads the company name and the home page <title> only.
    A local shop advertising against a franchise must not inherit its penalty."""
    html = """<html><head><title>Summit Ridge Plumbing | Family Owned in Boise</title></head>
      <body><h1>Summit Ridge Plumbing</h1>
      <p>Our drain cleaning costs less than Roto-Rooter and we beat Mr. Rooter on
      response time. Compare us to Benjamin Franklin Plumbing or Terminix.</p>
      </body></html>"""
    crawl = {"reachable": True, "https": True,
             "pages": {"home": {"url": "https://summitridgeplumbing.test/", "html": html}}}
    s = extract_signals(crawl, today=TODAY, company_name="Summit Ridge Plumbing")
    assert s["franchise"] is False
    assert "franchise" not in s["evidence"]


def test_franchise_brand_in_page_title_is_detected():
    """The counterpart: the brand in the site's own title does count."""
    html = "<html><head><title>Roto-Rooter of Boise | Plumbing</title></head><body>Plumbing</body></html>"
    crawl = {"reachable": True, "https": True,
             "pages": {"home": {"url": "https://example.test/", "html": html}}}
    s = extract_signals(crawl, today=TODAY, company_name="Boise Drain Pros")
    assert s["franchise"] is True
    assert s["evidence"]["franchise"]["page"] == "home"
