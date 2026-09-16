"""Generate the demo dataset.

All companies, people and domains are fictional. Domains use the reserved
.test TLD so they can never collide with a real business.

Outputs:
  data/sample_leads.csv   - looks like a SaaSquatch export (with duplicates and gaps)
  data/demo_sites.json    - recorded website pages served when DEMO_MODE=true
"""
import csv
import json
from pathlib import Path

DATA = Path(__file__).resolve().parents[1] / "data"


def page(title, body, *, year=2024, viewport=True, extra_head="", nav=("about", "services", "contact")):
    links = "".join(f'<a href="/{n}">{n.title()}</a> ' for n in nav)
    vp = '<meta name="viewport" content="width=device-width, initial-scale=1">' if viewport else ""
    return (f"<html><head><title>{title}</title>{vp}{extra_head}</head><body>"
            f"<nav><a href='/'>Home</a> {links}</nav><main>{body}</main>"
            f"<footer>&copy; {year} {title}. All rights reserved.</footer></body></html>")


SITES = {
    "reyescomfort.test": dict(
        title="Reyes Comfort Heating & Air", year=2018, viewport=False,
        head='<meta name="description" content="Family-owned heating and air conditioning service for Phoenix homes and businesses since 1989."><link href="/wp-content/themes/hvac/style.css">',
        home="<h1>Phoenix heating and air conditioning you can count on</h1><p>Family-owned since 1989. Call (602) 555-0141 for same-day AC repair, furnace service and new installs.</p><p>Ask about our Comfort Club maintenance plan: two tune-ups a year and priority service.</p><p>Read what our customers say: over 900 5-star reviews.</p>",
        about="<h2>Our story</h2><p>Frank Reyes, owner, started the company out of his garage in 1989. Today our team of 42 technicians and staff serves the entire Valley.</p><p>After 35 years, Frank is thinking about the next chapter and wants the team and customers taken care of for decades to come.</p>",
        services="<h2>Services</h2><p>AC repair, furnace repair, duct cleaning, commercial service agreements for property managers.</p>",
        contact="<p>Email frank@reyescomfort.test or office@reyescomfort.test. Phone (602) 555-0141.</p>",
    ),
    "summitridgeplumbing.test": dict(
        title="Summit Ridge Plumbing", year=2021,
        head='<meta name="description" content="Denver plumbing, drain cleaning and water heater experts.">',
        home="<h1>Denver's plumbing team since 1996</h1><p>Drain cleaning, water heater installs and repiping. Join the Summit Ridge membership for annual inspections and 15% off repairs.</p>",
        about="<p>Dale Hughes, founder, grew Summit Ridge from one truck to a crew of 28 licensed plumbers.</p>",
        services="<p>Water heater replacement, sewer line repair, plumbing inspections.</p>",
        contact="<p>Reach us at (303) 555-0199 or service@summitridgeplumbing.test.</p>",
        nav=("about", "services", "contact", "careers"),
        careers="<h2>Now hiring</h2><p>Join our team of plumbers. Open positions for apprentices.</p>",
    ),
    "brightlineit.test": dict(
        title="Brightline Managed IT", year=2026,
        head='<meta name="description" content="Managed IT and cybersecurity for Austin small businesses."><script src="https://www.googletagmanager.com/gtag/js"></script><script src="//js.hs-scripts.com/1.js"></script><script src="https://widget.intercom.io/x.js"></script>',
        home="<h1>Managed IT that just works</h1><p>Founded in 2011. Flat-rate managed services and 24/7 cybersecurity monitoring on simple monthly plans.</p><a href='https://calendly.com/brightline'>Book online</a>",
        about="<p>Priya Raman, CEO, leads a team of 60 engineers across Texas.</p>",
        services="<p>Managed services, help desk, cloud migration, compliance.</p>",
        contact="<p>hello@brightlineit.test · (512) 555-0110</p>",
    ),
    "oakhavenlandscaping.test": dict(
        title="Oakhaven Landscaping", year=2016, viewport=False,
        head='<meta name="description" content="Commercial and residential landscaping in Charlotte.">',
        home="<h1>Beautiful grounds, every season</h1><p>A second-generation, family-owned landscaping company serving Charlotte for over 30 years.</p><p>Annual service contracts for HOAs and office parks, plus seasonal lawn care.</p>",
        about="<p>Owner Tom Whitfield took over from his father and runs a crew of 18.</p>",
        services="<p>Lawn care, irrigation, hardscaping, annual maintenance agreements.</p>",
        contact="<p>Call (704) 555-0122 or email tom@oakhavenlandscaping.test</p>",
    ),
    "precisionedgemfg.test": dict(
        title="Precision Edge Machining", year=2019,
        head='<meta name="description" content="CNC machining and metal fabrication in Cleveland, Ohio.">',
        home="<h1>Tight tolerances since 1978</h1><p>Established in 1978, Precision Edge provides CNC machining and fabrication for aerospace and medical customers.</p>",
        about="<p>Gary Novak, President, joined his uncle's shop in 1985. Our staff of 85 people runs two shifts.</p>",
        services="<p>CNC milling, turning, welding and fabrication, prototype runs.</p>",
        contact="<p>sales@precisionedgemfg.test (216) 555-0133</p>",
    ),
    "harborpointpest.test": dict(
        title="Harbor Point Pest Control", year=2025,
        head='<script src="https://www.googletagmanager.com/gtag/js"></script>',
        home="<h1>Tampa pest control</h1><p>Serving Tampa Bay since 2005 with quarterly pest control plans and termite protection. Book online today.</p><p>Each location is an independently owned and operated franchise.</p>",
        about="<p>Our team of 22 pest control professionals.</p>",
        services="<p>Termite inspections, mosquito treatment, monthly service for restaurants.</p>",
        contact="<p>(813) 555-0190 info@harborpointpest.test</p>",
    ),
    "keystoneclean.test": dict(
        title="Keystone Commercial Cleaning", year=2025,
        home="<h1>Janitorial services for Pittsburgh offices</h1><p>Founded in 2002. Commercial cleaning under flexible service agreements.</p>",
        about="<p>Keystone is a portfolio company of Allegheny Growth Capital. Our staff of 120 people cleans over 300 buildings.</p>",
        services="<p>Janitorial contracts, floor care, post-construction cleaning.</p>",
        contact="<p>info@keystoneclean.test (412) 555-0155</p>",
    ),
    "lumendigital.test": dict(
        title="Lumen Digital Studio", year=2026,
        head='<script src="https://www.googletagmanager.com/gtag/js"></script><script src="https://embed.tawk.to/x"></script>',
        home="<h1>Brands that move people</h1><p>A Brooklyn digital marketing agency founded in 2020. SEO services, paid social and web design on a monthly retainer.</p><a href='https://calendly.com/lumen'>Book online</a>",
        about="<p>Co-founder Jess Park and a team of 9 designers and strategists.</p>",
        services="<p>Digital marketing, branding, SEO services.</p>",
        contact="<p>hello@lumendigital.test</p>",
    ),
    "cedarstonecpa.test": dict(
        title="Cedar & Stone Accounting", year=2020,
        head='<meta name="description" content="Tax preparation, bookkeeping and advisory for Madison families and small businesses.">',
        home="<h1>Trusted accounting for Madison since 1985</h1><p>Tax preparation and bookkeeping for over 600 local businesses and families. Monthly service packages for bookkeeping and payroll.</p>",
        about="<p>Margaret Olsen, founder, opened the firm in 1985. As she plans her retirement, she is focused on succession so clients keep the same care. Our staff of 14 includes 5 CPAs.</p>",
        services="<p>Tax preparation, bookkeeping, payroll, annual inspections of books for nonprofits.</p>",
        contact="<p>margaret@cedarstonecpa.test (608) 555-0170</p>",
    ),
    "deltafreightlines.test": dict(
        title="Delta Freight Lines", year=2023,
        home="<h1>Regional trucking and logistics</h1><p>Moving freight across the Mid-South since 1972 with dedicated contract carriage and warehousing.</p>",
        about="<p>President Carl Jennings leads more than 210 employees and 140 trucks.</p>",
        services="<p>Truckload freight, warehousing, dedicated fleets.</p>",
        contact="<p>dispatch@deltafreightlines.test (901) 555-0102</p>",
    ),
    "northwindroofing.test": dict(__blocked__=True),
}

CHALLENGE = ("<html><head><title>Just a moment...</title></head><body><div id='cf-chl-widget'>"
             "Checking your browser before accessing the site.</div></body></html>")


def build_sites():
    out = {}
    for domain, s in SITES.items():
        if s.get("__blocked__"):
            out[domain] = {"__status__": 403, "/": CHALLENGE}
            continue
        nav = s.get("nav", ("about", "services", "contact"))
        common = dict(year=s["year"], viewport=s.get("viewport", True), extra_head=s.get("head", ""), nav=nav)
        site = {"/": page(s["title"], s["home"], **common)}
        for section in nav:
            site[f"/{section}"] = page(s["title"], s[section], **common)
        out[domain] = site
    return out


LEADS = [
    # Company Name, Website, Industry, City, State, Employee Count, Revenue Estimate, Owner, Email, Phone
    ["Reyes Comfort Heating & Air", "reyescomfort.test", "HVAC", "Phoenix", "AZ", "", "$5M-$10M", "", "", ""],
    ["Summit Ridge Plumbing", "https://summitridgeplumbing.test", "Plumbing", "Denver", "CO", "25", "$3M-$5M", "Dale Hughes", "", "303-555-0199"],
    ["Brightline Managed IT", "brightlineit.test", "IT Services", "Austin", "TX", "51-100", "$10M-$20M", "", "", ""],
    ["Oakhaven Landscaping", "www.oakhavenlandscaping.test", "Landscaping", "Charlotte", "NC", "11-50", "$1M-$3M", "", "", ""],
    ["Precision Edge Machining", "precisionedgemfg.test", "Manufacturing", "Cleveland", "OH", "85", "$10M-$20M", "", "", ""],
    ["Harbor Point Pest Control", "harborpointpest.test", "Pest Control", "Tampa", "FL", "22", "$1M-$3M", "", "", ""],
    ["Keystone Commercial Cleaning", "keystoneclean.test", "Commercial Cleaning", "Pittsburgh", "PA", "120", "$5M-$10M", "", "", ""],
    ["Lumen Digital Studio", "lumendigital.test", "Marketing Agency", "Brooklyn", "NY", "9", "$1M-$3M", "", "", ""],
    ["Cedar & Stone Accounting", "cedarstonecpa.test", "Accounting", "Madison", "WI", "14", "$1M-$3M", "", "", ""],
    ["Delta Freight Lines", "deltafreightlines.test", "Logistics", "Memphis", "TN", "210", "$20M-$50M", "", "", ""],
    ["Northwind Roofing", "northwindroofing.test", "Roofing", "Minneapolis", "MN", "35", "$3M-$5M", "", "", ""],
    ["Valley Auto Repair", "", "Auto Repair", "Fresno", "CA", "8", "$500K-$1M", "Luis Moreno", "valleyautofresno@gmail.com", "(559) 555-0187"],
    ["Old Town Electric", "oldtownelectric.test", "Electrical", "Richmond", "VA", "12", "$1M-$3M", "", "", ""],
    # Duplicates a real export would contain
    ["Reyes Comfort Heating and Air LLC", "https://www.reyescomfort.test/", "HVAC", "Phoenix", "AZ", "42", "", "", "", "(602) 555-0141"],
    ["Summit Ridge Plumbing, Inc.", "SummitRidgePlumbing.test", "Plumbing", "Denver", "CO", "", "", "", "", ""],
    ["", "nameless.test", "", "", "", "", "", "", "", ""],
]


def main():
    DATA.mkdir(exist_ok=True)
    (DATA / "demo_sites.json").write_text(json.dumps(build_sites(), indent=1))
    with open(DATA / "sample_leads.csv", "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["Company Name", "Website", "Industry", "City", "State", "Employee Count",
                    "Revenue Estimate", "Owner", "Email", "Phone"])
        w.writerows(LEADS)
    print(f"Wrote {len(LEADS)} rows and {len(SITES)} demo sites to {DATA}")


if __name__ == "__main__":
    main()
