import asyncio
import csv
import io
import logging
import os
import uuid
from contextlib import asynccontextmanager
from datetime import datetime, timezone
from pathlib import Path

from fastapi import BackgroundTasks, Depends, FastAPI, HTTPException, Query, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.gzip import GZipMiddleware
from fastapi.responses import StreamingResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field
from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session

from . import scraper
from .brief import generate_brief
from .db import Base, SessionLocal, engine, get_db
from .extract import extract_signals
from .ingest import parse_csv
from .models import Job, Lead, Setting
from .scoring import DEFAULT_ICP, score_lead
from .validate import classify_email, has_mx, normalize_phone, pick_best_email

ROOT = Path(__file__).resolve().parents[2]
SAMPLE_CSV = ROOT / "data" / "sample_leads.csv"
FRONTEND_DIST = ROOT / "frontend" / "dist"
CONCURRENCY = int(os.getenv("CRAWL_CONCURRENCY", "8"))

log = logging.getLogger("dealsieve")
if not log.handlers:  # uvicorn only configures its own loggers, so attach ours
    _handler = logging.StreamHandler()
    _handler.setFormatter(logging.Formatter("%(levelname)s:     %(message)s"))
    log.addHandler(_handler)
    log.setLevel(logging.INFO)


def seed_demo_enabled() -> bool:
    return os.getenv("SEED_DEMO", "false").lower() in ("1", "true", "yes")


async def seed_demo_data():
    """Import and score the sample dataset once, on an empty database.

    A reviewer opening a fresh deployment should land on a scored dashboard
    rather than an empty state. Only runs in demo mode, so it never crawls real
    sites, and any failure is logged and swallowed -- an empty dashboard is a
    much better outcome than an API that won't boot.
    """
    try:
        with SessionLocal() as db:
            if db.scalar(select(func.count(Lead.id))):
                return  # someone has already imported leads; leave them alone
            report = import_rows(db, SAMPLE_CSV.read_bytes())
            ids = list(db.scalars(select(Lead.id).where(Lead.status == "pending")).all())
            if not ids:
                return
            job = Job(id=uuid.uuid4().hex[:12], total=len(ids), status="running")
            db.add(job)
            db.commit()
            job_id = job.id
        log.info("SEED_DEMO: imported %s sample leads, enriching", report["added"])
        await run_enrichment(job_id, ids)
        log.info("SEED_DEMO: enrichment finished")
    except Exception as exc:  # noqa: BLE001 - startup must survive any seed failure
        log.warning("SEED_DEMO failed (%s): %s", type(exc).__name__, exc)


@asynccontextmanager
async def lifespan(_app: FastAPI):
    Base.metadata.create_all(bind=engine)
    task = None
    if seed_demo_enabled() and scraper.demo_mode():
        # fire and forget: startup must not wait on a crawl
        task = asyncio.create_task(seed_demo_data())
    yield
    if task and not task.done():
        task.cancel()


app = FastAPI(title="DealSieve API", version="1.0.0", lifespan=lifespan)
app.add_middleware(GZipMiddleware, minimum_size=1000)
app.add_middleware(
    CORSMiddleware,
    allow_origins=os.getenv("CORS_ORIGINS", "http://localhost:5173").split(","),
    allow_methods=["*"],
    allow_headers=["*"],
)


# ---- helpers -------------------------------------------------------------------
def get_icp(db: Session) -> dict:
    row = db.get(Setting, "icp")
    return {**DEFAULT_ICP, **(row.value if row else {})}


def lead_to_dict(lead: Lead, full: bool = False) -> dict:
    s = lead.signals or {}
    data = {
        "id": lead.id, "name": lead.name, "domain": lead.domain, "city": lead.city, "state": lead.state,
        "industry": lead.industry or s.get("industry_guess"), "employees": lead.employees or s.get("employees_hint"),
        "revenue_estimate": lead.revenue_estimate, "owner_name": lead.owner_name or s.get("owner_name"),
        "email": lead.email, "email_status": lead.email_status, "phone": lead.phone,
        "status": lead.status, "score": lead.score, "tier": lead.tier, "confidence": lead.confidence,
        "breakdown": lead.breakdown or [], "flags": lead.flags or [], "stage": lead.stage,
        "years_in_business": s.get("years_in_business"),
        "tags": {
            "succession": bool(s.get("succession")), "family_owned": bool(s.get("family_owned")),
            "recurring": bool(s.get("recurring_terms")), "hiring": bool(s.get("hiring")),
        },
    }
    if full:
        data.update({"signals": s, "notes": lead.notes, "brief": lead.brief, "error": lead.error,
                     "enriched_at": lead.enriched_at.isoformat() if lead.enriched_at else None})
    return data


def rescore(lead: Lead, icp: dict):
    base = {"employees": lead.employees, "industry": lead.industry, "owner_name": lead.owner_name,
            "phone": lead.phone, "email_status": lead.email_status, "domain": lead.domain}
    result = score_lead(base, lead.signals or {}, icp)
    lead.score, lead.tier, lead.confidence = result["score"], result["tier"], result["confidence"]
    lead.breakdown, lead.flags = result["breakdown"], result["flags"]


def filtered_query(db: Session, q, tiers, min_score, industry, stage, has_email, succession, status):
    stmt = select(Lead)
    if q:
        like = f"%{q.lower()}%"
        stmt = stmt.where(or_(func.lower(Lead.name).like(like), func.lower(Lead.domain).like(like),
                              func.lower(Lead.city).like(like)))
    if tiers:
        stmt = stmt.where(Lead.tier.in_([t.strip().upper() for t in tiers.split(",") if t.strip()]))
    if min_score:
        stmt = stmt.where(Lead.score >= min_score)
    if industry:
        stmt = stmt.where(func.lower(Lead.industry) == industry.lower())
    if stage:
        stmt = stmt.where(Lead.stage.in_(stage.split(",")))
    if has_email:
        stmt = stmt.where(Lead.email_status.in_(["valid", "personal_domain"]))
    if status:
        stmt = stmt.where(Lead.status == status)
    leads = db.scalars(stmt).all()
    if succession:  # JSON filtering kept in Python for SQLite/Postgres portability
        leads = [l for l in leads if (l.signals or {}).get("succession") or (l.signals or {}).get("family_owned")]
    return leads


# ---- import ----------------------------------------------------------------------
def import_rows(db: Session, content: bytes) -> dict:
    try:
        rows, report = parse_csv(content)
    except ValueError as exc:
        raise HTTPException(400, str(exc))

    batch = uuid.uuid4().hex[:12]
    added = merged = 0
    icp = get_icp(db)
    for row in rows:
        existing = None
        if row["domain"]:
            existing = db.scalar(select(Lead).where(Lead.domain == row["domain"]))
        if not existing:
            existing = db.scalar(select(Lead).where(Lead.name_key == row["name_key"], Lead.city == row["city"]))
        if existing:
            for k, v in row.items():
                if v and not getattr(existing, k):
                    setattr(existing, k, v)
            merged += 1
            continue
        lead = Lead(batch_id=batch, **row)
        lead.phone = normalize_phone(lead.phone)
        rescore(lead, icp)
        db.add(lead)
        added += 1
    db.commit()
    report.update({"batch_id": batch, "added": added, "already_in_pipeline": merged})
    return report


@app.post("/api/leads/import")
async def import_csv(file: UploadFile, db: Session = Depends(get_db)):
    content = await file.read()
    if len(content) > 5_000_000:
        raise HTTPException(413, "File is larger than 5 MB. Split it into smaller files.")
    return import_rows(db, content)


@app.post("/api/leads/import-sample")
def import_sample(db: Session = Depends(get_db)):
    return import_rows(db, SAMPLE_CSV.read_bytes())


# ---- enrichment ----------------------------------------------------------------
class EnrichRequest(BaseModel):
    lead_ids: list[int] | None = None
    force: bool = False


async def run_enrichment(job_id: str, lead_ids: list[int]):
    demo = scraper.demo_mode()
    demo_sites = scraper.load_demo_sites() if demo else None
    fetcher = scraper.Fetcher(concurrency=CONCURRENCY, demo_sites=demo_sites)
    mx_lookup = (lambda host: host in demo_sites or None) if demo else has_mx
    lock = asyncio.Lock()
    limiter = asyncio.Semaphore(CONCURRENCY)

    async def process(lead_id: int):
        ok = True
        async with limiter:
            with SessionLocal() as db:
                lead = db.get(Lead, lead_id)
                if not lead:
                    return
                try:
                    if lead.domain:
                        crawl = await scraper.crawl_site(fetcher, lead.domain)
                    else:
                        crawl = {"reachable": False, "error": "No website on record", "pages": {}}
                    signals = extract_signals(crawl, company_name=lead.name)
                    if not lead.email and signals.get("emails"):
                        lead.email = pick_best_email(signals["emails"], lead.owner_name or signals.get("owner_name"), lead.domain)
                    if not lead.phone and signals.get("phones"):
                        lead.phone = signals["phones"][0]
                    lead.phone = normalize_phone(lead.phone)
                    lead.email_status = await asyncio.to_thread(classify_email, lead.email, lead.domain, mx_lookup)
                    lead.signals = signals
                    lead.status = "enriched" if signals["reachable"] else "failed"
                    lead.error = signals.get("crawl_error")
                    ok = signals["reachable"]
                except Exception as exc:  # one bad site must never kill the batch
                    lead.status, lead.error, ok = "failed", f"Unexpected error: {type(exc).__name__}", False
                lead.enriched_at = datetime.now(timezone.utc)
                rescore(lead, get_icp(db))
                db.commit()
        async with lock:
            with SessionLocal() as db:
                job = db.get(Job, job_id)
                job.done += 1
                job.failed += 0 if ok else 1
                db.commit()

    try:
        await asyncio.gather(*(process(i) for i in lead_ids))
    finally:
        await fetcher.close()
        with SessionLocal() as db:
            job = db.get(Job, job_id)
            job.status, job.finished_at = "finished", datetime.now(timezone.utc)
            db.commit()


@app.post("/api/enrich")
def start_enrichment(req: EnrichRequest, background: BackgroundTasks, db: Session = Depends(get_db)):
    stmt = select(Lead.id)
    if req.lead_ids:
        stmt = stmt.where(Lead.id.in_(req.lead_ids))
    if not req.force:
        stmt = stmt.where(Lead.status == "pending")
    ids = list(db.scalars(stmt).all())
    job = Job(id=uuid.uuid4().hex[:12], total=len(ids), status="running" if ids else "finished")
    db.add(job)
    db.commit()
    if ids:
        background.add_task(run_enrichment, job.id, ids)
    return {"job_id": job.id, "total": len(ids)}


@app.get("/api/jobs/{job_id}")
def job_status(job_id: str, db: Session = Depends(get_db)):
    job = db.get(Job, job_id)
    if not job:
        raise HTTPException(404, "Job not found")
    return {"id": job.id, "total": job.total, "done": job.done, "failed": job.failed, "status": job.status}


# ---- leads ------------------------------------------------------------------------
SORTS = {"score": lambda l: (l.score, l.confidence), "name": lambda l: l.name.lower(),
         "years": lambda l: (l.signals or {}).get("years_in_business") or -1,
         "confidence": lambda l: l.confidence}


@app.get("/api/leads")
def list_leads(
    q: str | None = None, tiers: str | None = None, min_score: int = 0, industry: str | None = None,
    stage: str | None = None, has_email: bool = False, succession: bool = False, status: str | None = None,
    sort: str = "score", order: str = "desc", db: Session = Depends(get_db),
):
    leads = filtered_query(db, q, tiers, min_score, industry, stage, has_email, succession, status)
    leads.sort(key=SORTS.get(sort, SORTS["score"]), reverse=order == "desc")
    return {"items": [lead_to_dict(l) for l in leads], "count": len(leads)}


@app.get("/api/leads/{lead_id}")
def get_lead(lead_id: int, db: Session = Depends(get_db)):
    lead = db.get(Lead, lead_id)
    if not lead:
        raise HTTPException(404, "Lead not found")
    return lead_to_dict(lead, full=True)


class LeadUpdate(BaseModel):
    stage: str | None = Field(None, pattern="^(new|shortlist|contacted|passed)$")
    notes: str | None = Field(None, max_length=5000)


@app.patch("/api/leads/{lead_id}")
def update_lead(lead_id: int, body: LeadUpdate, db: Session = Depends(get_db)):
    lead = db.get(Lead, lead_id)
    if not lead:
        raise HTTPException(404, "Lead not found")
    if body.stage is not None:
        lead.stage = body.stage
    if body.notes is not None:
        lead.notes = body.notes
    db.commit()
    return lead_to_dict(lead, full=True)


@app.post("/api/leads/{lead_id}/brief")
async def make_brief(lead_id: int, db: Session = Depends(get_db)):
    lead = db.get(Lead, lead_id)
    if not lead:
        raise HTTPException(404, "Lead not found")
    brief = await generate_brief(lead_to_dict(lead, full=True))
    lead.brief = brief
    db.commit()
    return brief


@app.delete("/api/leads")
def clear_leads(db: Session = Depends(get_db)):
    db.query(Lead).delete()
    db.commit()
    return {"ok": True}


# ---- settings & stats -------------------------------------------------------------
class ICPUpdate(BaseModel):
    target_industries: list[str]
    employees_min: int = Field(ge=0)
    employees_max: int = Field(ge=1)
    min_years: int = Field(ge=0, le=100)
    weights: dict[str, int]


@app.get("/api/settings")
def read_settings(db: Session = Depends(get_db)):
    return get_icp(db)


@app.put("/api/settings")
def save_settings(body: ICPUpdate, db: Session = Depends(get_db)):
    if body.employees_min > body.employees_max:
        raise HTTPException(400, "Minimum employees can't be larger than maximum.")
    value = body.model_dump()
    db.merge(Setting(key="icp", value=value))
    icp = {**DEFAULT_ICP, **value}
    leads = db.scalars(select(Lead)).all()
    for lead in leads:  # no re-crawl needed: signals are stored separately from scores
        rescore(lead, icp)
    db.commit()
    return {"icp": icp, "rescored": len(leads)}


@app.get("/api/stats")
def stats(db: Session = Depends(get_db)):
    leads = db.scalars(select(Lead)).all()
    industries = sorted({l.industry or (l.signals or {}).get("industry_guess") for l in leads} - {None})
    return {
        "total": len(leads),
        "pending": sum(l.status == "pending" for l in leads),
        "enriched": sum(l.status == "enriched" for l in leads),
        "failed": sum(l.status == "failed" for l in leads),
        "tiers": {t: sum(l.tier == t for l in leads if l.status != "pending") for t in "ABCD"},
        "stages": {s: sum(l.stage == s for l in leads) for s in ("new", "shortlist", "contacted", "passed")},
        "industries": industries,
        "signals": {
            "owner_transition": sum(bool((l.signals or {}).get("succession") or (l.signals or {}).get("family_owned")) for l in leads),
            "direct_email": sum(l.email_status in ("valid", "personal_domain") for l in leads),
        },
        "demo_mode": scraper.demo_mode(),
        "ai_briefs": bool(os.getenv("ANTHROPIC_API_KEY")),
    }


# ---- export ------------------------------------------------------------------------
@app.get("/api/export.csv")
def export_csv(
    q: str | None = None, tiers: str | None = None, min_score: int = 0, industry: str | None = None,
    stage: str | None = None, has_email: bool = False, succession: bool = False,
    db: Session = Depends(get_db),
):
    leads = filtered_query(db, q, tiers, min_score, industry, stage, has_email, succession, None)
    leads.sort(key=SORTS["score"], reverse=True)
    buf = io.StringIO()
    w = csv.writer(buf)
    # Column names match HubSpot's default import properties, so the file maps with zero clicks.
    w.writerow(["Company name", "Company Domain Name", "First Name", "Last Name", "Email", "Phone Number",
                "City", "State/Region", "Industry", "Number of Employees", "Year Founded",
                "Acquisition Fit Score", "Fit Tier", "Data Confidence", "Email Status", "Why It Fits",
                "Risks", "Pipeline Stage", "Notes"])
    for l in leads:
        d = lead_to_dict(l, full=True)
        first, _, last = (d["owner_name"] or "").partition(" ")
        top = sorted(d["breakdown"], key=lambda b: -b["points"])[:3]
        w.writerow([d["name"], d["domain"] or "", first, last, d["email"] or "", d["phone"] or "",
                    d["city"] or "", d["state"] or "", d["industry"] or "", d["employees"] or "",
                    (d["signals"] or {}).get("founded_year") or "", d["score"], d["tier"], f"{d['confidence']}%",
                    d["email_status"] or "", "; ".join(b["reason"] for b in top),
                    "; ".join(f["text"] for f in d["flags"] if f["level"] != "good"), d["stage"], d["notes"] or ""])
    buf.seek(0)
    stamp = datetime.now().strftime("%Y-%m-%d")
    return StreamingResponse(iter([buf.getvalue()]), media_type="text/csv",
                             headers={"Content-Disposition": f'attachment; filename="dealsieve-leads-{stamp}.csv"'})


@app.get("/api/health")
def health():
    return {"ok": True}


# Serve the built React app from the same container in production.
if FRONTEND_DIST.exists():
    app.mount("/", StaticFiles(directory=FRONTEND_DIST, html=True), name="frontend")
