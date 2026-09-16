import asyncio
from pathlib import Path

from fastapi.testclient import TestClient

from app.db import Base, SessionLocal, engine
from app.main import app, run_enrichment
from app.models import Job


def setup_module():
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)


def teardown_module():
    Path("test_dealsieve.db").unlink(missing_ok=True)


def test_full_workflow():
    client = TestClient(app)
    report = client.post("/api/leads/import-sample").json()
    assert report["added"] == 13, report
    assert report["duplicates_in_file"] == 2

    assert client.post("/api/leads/import-sample").json()["added"] == 0  # idempotent

    ids = [l["id"] for l in client.get("/api/leads").json()["items"]]
    with SessionLocal() as db:
        db.add(Job(id="testjob", total=len(ids)))
        db.commit()
    asyncio.run(run_enrichment("testjob", ids))

    leads = client.get("/api/leads").json()["items"]
    by_name = {l["name"]: l for l in leads}
    for l in leads:
        print(l["score"], l["tier"], l["confidence"], l["name"], l["email"], l["email_status"])
    assert leads[0]["tier"] == "A"
    assert by_name["Reyes Comfort Heating & Air"]["email"] == "frank@reyescomfort.test"
    assert by_name["Reyes Comfort Heating & Air"]["phone"] == "(602) 555-0141"
    assert any("bot check" in f["text"] for f in by_name["Northwind Roofing"]["flags"])
    assert by_name["Valley Auto Repair"]["email_status"] == "personal_domain"

    stats = client.get("/api/stats").json()
    assert stats["enriched"] == 10 and stats["failed"] == 3, stats

    brief = client.post(f"/api/leads/{by_name['Cedar & Stone Accounting']['id']}/brief").json()
    assert brief["source"] == "template" and "Margaret" in brief["email_body"]

    lead_id = by_name["Oakhaven Landscaping"]["id"]
    assert client.patch(f"/api/leads/{lead_id}", json={"stage": "shortlist"}).json()["stage"] == "shortlist"

    icp = client.get("/api/settings").json()
    icp["weights"]["upside"] = 0
    assert client.put("/api/settings", json=icp).json()["rescored"] == 13

    export = client.get("/api/export.csv?tiers=A,B")
    assert export.status_code == 200
    assert export.text.splitlines()[0].startswith("Company name,Company Domain Name")
