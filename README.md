# DealSieve

**Acquisition-fit scoring for SaaSquatch leads.** Import a lead list, and DealSieve reads each company's website, finds the signals that matter to someone buying a small business, and ranks every lead with a score you can explain line by line.

> Demo: _add your deployed link here_  ·  Video walkthrough: _add link here_

---

## 1. The problem

SaaSquatch is excellent at the top of the funnel: it finds companies, estimates revenue, and enriches contacts. But its core users are **searchers, ETA entrepreneurs and acquirers**, not traditional SDRs. Their question isn't "who might buy my product?". It's:

> *"Out of these 500 businesses, which 20 are worth an owner call this week?"*

Today that answer comes from opening websites one by one and guessing. A generic lead score doesn't help, because the signals that make a business a good **acquisition** target are different from the ones that make a good **sales** prospect:

| Sales lead scoring looks for | Acquisition scoring looks for |
|---|---|
| Fast growth, funding, new tech | 20+ years of durable operations |
| Big budgets | Recurring revenue (maintenance plans, service contracts) |
| Decision-maker titles | An owner who may be ready to step back |
| Modern stack (easy integration) | A dated web presence (room for post-acquisition value creation) |
| — | **Not** already PE-backed or a franchise |

This matches Caprae's thesis: value is created *after* the acquisition, often by bringing AI and modern operations to a solid, under-digitized business.

## 2. What I built (Quality First)

I chose to go deep on one workflow rather than wide on many tools.

1. **Smart import.** Drop any CSV (SaaSquatch export, HubSpot, Apollo). Column names are auto-mapped, websites and emails are normalized, duplicates are merged (`Reyes Comfort Heating & Air` and `Reyes Comfort Heating and Air LLC` at `www.reyescomfort.test/` become one record), and re-importing the same file adds nothing.
2. **Website enrichment.** An async crawler visits up to 5 pages per company (home, about, services, contact, careers) and extracts: founding year, owner name, family ownership, succession/retirement language, recurring-revenue offers, headcount hints, emails, phones, social links, and a digital-maturity profile (CMS, HTTPS, mobile-friendly, online booking, chat, analytics).
3. **Explainable Acquisition Fit Score (0–100).** Seven weighted components in three groups: *Is it a solid business? / Is there an opportunity? / Can you reach the owner?* Risk deductions for PE-backed companies and franchises. A **confidence %** shows how much was actually found versus estimated.
4. **Evidence, not a black box.** Every signal stores the sentence it came from and the page it was on. Users see *"…After 35 years, Frank is thinking about the next chapter…" (about page)* next to the score.
5. **Adjustable buy box.** Change target industries, headcount range, minimum years, or any weight, and all leads are **rescored instantly without re-crawling**, because signals and scores are stored separately.
6. **Contact validation.** Syntax, role-inbox detection (`info@`, `dispatch@`), personal-domain detection, and DNS MX lookup. The best address is chosen automatically (owner's name first).
7. **Owner outreach brief.** One click produces a summary, why-it-fits, risks, first-call questions and a respectful first email. It uses Claude when `ANTHROPIC_API_KEY` is set, and falls back to a deterministic template, so the feature never breaks.
8. **Pipeline + CRM export.** Stage (New / Shortlist / Contacted / Passed) and notes per lead, and a filtered CSV export whose headers match HubSpot's default import properties.

## 3. UX decisions

- **Feels native to SaaSquatch Leads.** The dashboard uses the same visual language as SaaSquatch (deep navy surfaces, teal-to-sky gradient on primary actions, tinted icon tiles, dark data tables inside rounded panels) and the same app structure: a left sidebar for navigation and a toolbar with search, filters and export above the table. It reads as a module of the existing product.
- **Overview cards are filters.** "Strong fit", "Owner transition" and "Direct owner email" show counts and narrow the table in one click, so the most common questions take zero typing.
- **Pipeline in the sidebar.** All leads, Shortlist, Contacted and Passed act like saved views with live counts.

- **The score shows its own reasoning.** In the table, each score is drawn as a stacked bar of its components, colored by group (teal = solid business, sky blue = opportunity, violet = reachable). You can see *why* a 74 is a 74 without opening anything. Faded segments mean "estimated, not found".
- **A visible four-step flow** (Import → Enrich → Review → Export) in the header tells a first-time user where they are and what comes next.
- **Empty states give direction.** The first screen explains the value in one sentence and offers "Try with sample leads", so no one has to find a CSV to understand the tool.
- **Honest uncertainty.** Leads with little data say "Needs manual review" instead of pretending to be a weak fit. Unreachable and bot-protected sites are flagged, not silently scored low.
- **Work doesn't block.** Enrichment runs in the background with a live progress bar; scores fill into the table as each company finishes.
- **Filters match how searchers think:** fit-tier chips with counts, minimum score, industry, owner transition, direct owner email, and pipeline stage.
- **Accessibility floor:** keyboard-navigable rows (Enter opens), Escape closes panels, visible focus rings, ARIA labels on the score bars, `prefers-reduced-motion` and dark mode respected, responsive down to mobile.

## 4. Architecture

```mermaid
flowchart LR
  U[Browser<br/>React SPA] -->|REST /api| API[FastAPI<br/>Uvicorn]
  API --> ING[Import<br/>map, normalize, dedupe]
  API --> BG[Background enrichment<br/>asyncio tasks]
  BG --> CR[Crawler<br/>httpx async, robots.txt,<br/>retries, block detection]
  CR <--> CACHE[(PageCache table<br/>72h TTL)]
  CR --> EX[Signal extractor<br/>BeautifulSoup + regex]
  EX --> VAL[Contact validation<br/>dnspython MX]
  VAL --> SC[Scoring engine<br/>rules + ICP weights]
  SC --> DB[(Postgres / SQLite)]
  API --> BR[Brief generator] -->|optional| LLM[Anthropic API]
```

### Exact stack

| Layer | Technology | Why |
|---|---|---|
| Frontend | React 18, Vite 6, plain CSS with design tokens, Inter | Small bundle (55 KB gzipped JS), no UI-kit lock-in |
| API | Python 3.12, FastAPI 0.115, Uvicorn, Pydantic 2 | Async I/O fits crawling; typed request validation |
| Crawling | httpx (async), BeautifulSoup 4 | Concurrency without a headless browser's cost |
| Validation | dnspython | MX checks without risky SMTP probing |
| ORM | SQLAlchemy 2.0 | Same code on SQLite (dev) and Postgres (prod) |
| Database | **PostgreSQL 16** in production (Neon or Supabase), SQLite locally | JSON columns for signals, zero-setup local dev |
| AI | Anthropic Messages API (`claude-sonnet-4-6`), optional | Used only for writing, never for the score |
| Tests / CI | pytest, GitHub Actions | 23 tests covering import, extraction, scoring, franchise detection, demo seeding and the full API flow |
| Packaging | Multi-stage Dockerfile (Node build → Python slim) | One image serves API and static app |

### Data storage

- `leads`: imported fields, extracted `signals` (JSON), score, tier, confidence, `breakdown` (JSON), flags, stage, notes, brief. Unique index on `domain` enforces dedup at the database level.
- `page_cache`: raw HTML per URL with fetch time (TTL cache).
- `jobs`: enrichment progress for polling.
- `settings`: the user's ICP / weights.

### Caching and performance

- **HTTP response cache** in `page_cache` (72 h TTL, configurable). Re-running enrichment or re-checking a lead doesn't hit the website again.
- **Scores decoupled from crawling.** Changing the buy box rescores every lead in memory in milliseconds.
- **Bounded concurrency** (`CRAWL_CONCURRENCY`, default 8) with an async semaphore; each company is capped at 5 pages and 1.5 MB per page.
- **Retries with exponential backoff** on 429/5xx and timeouts; DNS/connection errors fail fast.
- **Failure isolation:** one broken site marks that lead `failed` and never stops the batch.
- **MX lookups** are LRU-cached per domain; GZip middleware compresses API responses.

### Scraping ethics and resilience

- Respects `robots.txt` and sends an identifiable User-Agent.
- Small delay between pages of the same site; only public business pages are read.
- **CAPTCHAs and bot walls are detected and flagged for manual review, not bypassed.** Rotating proxies or solving CAPTCHAs would break site terms, and for a firm whose brand is built on trust with business owners, that isn't worth a few extra leads.
- No SMTP "ping" email verification (it gets sending IPs blacklisted).

### Hosting and deployment

- **Hosting model:** a single **serverless container** (Google Cloud Run, or Render as an alternative). The React build is served as static files by the same container, so there's one deploy and no CORS setup. At larger scale, the static app moves to a CDN (Vercel / Cloud Storage + Cloud CDN).
- **Cloud provider:** GCP (Cloud Run + Artifact Registry), with Postgres on Neon or Supabase.
- **Deploy process:** push to `main` → GitHub Actions runs tests and the frontend build → `gcloud run deploy --source .` builds the Dockerfile and rolls out a new revision with zero downtime.

```bash
gcloud run deploy dealsieve --source . --region us-central1 --allow-unauthenticated \
  --set-env-vars DEMO_MODE=true,DATABASE_URL=postgresql://USER:PASS@HOST/db
```

- **Data persistence:** if `DATABASE_URL` is unset the app falls back to SQLite *inside the container*. On Render's free tier the filesystem is ephemeral, so leads reset whenever the instance restarts or spins down. That is fine for a demo — with `SEED_DEMO=true` it re-imports and re-scores the sample dataset on the next boot — but set `DATABASE_URL` to a Neon or Supabase Postgres URL for anything you need to keep.
- **Scaling path:** background enrichment currently runs in-process (fine for one instance and thousands of leads). The next step is moving crawl jobs to a queue (Cloud Tasks or Redis + RQ) so workers scale independently from the API.

## 5. Run it locally

**Requirements:** Python 3.12+, Node 20+.

```bash
# 1. Backend
cd backend
python -m venv .venv && source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install -r requirements.txt
DEMO_MODE=true uvicorn app.main:app --reload --port 8000
# Windows PowerShell: $env:DEMO_MODE="true"; uvicorn app.main:app --reload --port 8000

# 2. Frontend (new terminal)
cd frontend
npm install
npm run dev          # open http://localhost:5173
```

Click **Try with sample leads**, then **Score 13 leads**.

**Or with Docker (includes Postgres):**

```bash
docker compose up --build     # open http://localhost:8080
```

**Tests:**

```bash
cd backend && pytest -q
```

### Demo mode vs live mode

- `DEMO_MODE=true` serves recorded pages from `data/demo_sites.json`, so the demo is fast, offline and reproducible.
- `DEMO_MODE=false` crawls real websites. Import any real lead export.
- `SEED_DEMO=true` (demo mode only, default `false`) imports and scores the sample dataset at startup **if the leads table is empty**, so anyone opening a fresh deployment lands on a populated dashboard instead of an empty state. It runs as a background task, so it never delays startup, and it never touches a database that already has leads.

### Sample dataset

`data/sample_leads.csv` has 16 rows shaped like a SaaSquatch export, including two duplicates, one row without a name, one company with no website, one unreachable domain and one bot-protected site. **All companies, people and domains are fictional** and use the reserved `.test` domain. Regenerate with `python scripts/make_demo_data.py`.

### Real-world test

The demo dataset is fictional, so the crawler was also run in live mode
(`DEMO_MODE=false`, `CRAWL_CONCURRENCY=4`) against six real national service
brands, imported with only name, website, city and industry — no owner, email or
headcount — so enrichment had to find everything itself. The list is in
`data/real_leads_test.csv`.

**What the crawler did:** 22 URLs fetched and cached across the six companies.
Four sites crawled successfully; two were refused and flagged for manual review
rather than silently scored low — American Residential Services returned a bot
check, and TruGreen returned HTTP 403. One page
(`benjaminfranklinplumbing.com/locations/`) hit the 1.5 MB per-page cap and was
truncated as designed.

**What it extracted** from Roto-Rooter, across 5 pages (home, about, services,
contact, careers): founded **1935** (91 years), from the sentence *"Highly-trained
professionals since 1935"* on the home page; phone `(800) 768-6911`; Facebook,
Instagram and LinkedIn; and a digital-maturity score of 80 (HTTPS, mobile
friendly, online booking, analytics). Every one of those signals stores the page
it came from, so the score stays auditable on real data and not just on fixtures.

**What it got wrong, and the fix.** The first live run flagged Terminix and
ServiceMaster as franchises but **missed Roto-Rooter and Benjamin Franklin
Plumbing**, because neither uses the word "franchise" on the pages we crawl.
Franchise detection now also matches a list of known national franchise brands
against the company name and the home page `<title>` — deliberately not against
page text, so a local shop advertising "cheaper than Roto-Rooter" is not
penalised for naming a competitor. Matching on the name also works when a site
cannot be crawled at all, which is what now catches TruGreen behind its 403.

The phrases "locally owned and operated" and "independently owned and operated"
are handled more carefully, because independent businesses use them constantly
to distinguish themselves from the chains — and those are precisely the targets
this tool looks for. They only count as a franchise signal when the same page
also contains a franchise word or a known franchise brand. A family firm whose
about page says "locally owned and operated since 1985" keeps its score; a
footer reading "each location is an independently owned and operated franchise"
is still flagged. Given the deduction is 15 points, a false positive on a good
lead costs more than a missed franchise.
After the change, 5 of the 6 are flagged. The exception is American Residential
Services: it is bot-walled *and* its legal name contains no known brand, so it
stays unflagged — a real limitation, not a solved case.

| Company | Score before | Score after | Franchise |
|---|---|---|---|
| ServiceMaster Clean | 54 C | 54 C | ✅ both runs |
| Benjamin Franklin Plumbing | 68 B | 53 C | ➕ newly caught |
| Terminix | 52 C | 52 C | ✅ both runs |
| Roto-Rooter | 52 C | 37 D | ➕ newly caught |
| American Residential Services | 32 D | 32 D | ❌ still missed |
| TruGreen | 32 D | 17 D | ➕ newly caught (name only) |

**These low scores are the correct answer.** National franchise brands are not
acquisition targets for a searcher: they are far outside the buy box on
headcount, show no succession language, and carry the franchise deduction. A
scoring model that ranked them highly would be broken. The run was a test of
extraction and resilience on messy real HTML, not a search for real leads.

### Where to get real lead lists

- **A SaaSquatch export** is the intended source — the importer already aliases its column names, so the file needs no editing.
- **Google Places API** — best for targeting trades by geography; a generous free tier.
- **Apollo.io** — free tier includes exports, and carries headcount plus contact emails.
- **State business registries** — free, and the registration year is a pre-verified "years in business" signal.
- **BizBuySell** — businesses already listed for sale, so owner transition is implicit.

A good pairing is a cheap source for the list (Google Places) plus DealSieve's
crawler for the enrichment you would otherwise buy.

## 6. API

| Method | Path | Purpose |
|---|---|---|
| POST | `/api/leads/import` | Upload CSV (multipart) → import report |
| POST | `/api/leads/import-sample` | Load the sample dataset |
| POST | `/api/enrich` | Start enrichment `{lead_ids?, force?}` → `job_id` |
| GET | `/api/jobs/{id}` | Progress |
| GET | `/api/leads` | List with `q, tiers, min_score, industry, stage, has_email, succession, sort, order` |
| GET / PATCH | `/api/leads/{id}` | Detail with evidence / update stage and notes |
| POST | `/api/leads/{id}/brief` | Generate outreach brief |
| GET / PUT | `/api/settings` | Read / save buy box (rescores all leads) |
| GET | `/api/stats` | Counts for filters and progress |
| GET | `/api/export.csv` | HubSpot-ready CSV of the current filter |

Interactive docs: `http://localhost:8000/docs`.

## 7. Scoring model

| Group | Component | Default weight | Full points when |
|---|---|---|---|
| Solid business | Years in business | 20 | ≥ 2 × minimum years |
| | Company size | 15 | Inside the buy-box headcount range |
| | Industry fit | 15 | Matches a target industry |
| Opportunity | Recurring revenue | 15 | 2+ recurring offers mentioned |
| | Owner transition | 15 | Retirement / succession language |
| | Digital upside | 10 | Dated site, no booking, not mobile friendly |
| Access | Owner reachable | 10 | Direct email + phone + owner name |
| Deductions | PE-backed −25, franchise −15 | | |

Tiers: **A** ≥ 72, **B** ≥ 55, **C** ≥ 38, **D** below. Confidence = share of components backed by found data.

I kept the score rules-based on purpose: it's deterministic, auditable, free to recompute, and every point maps to evidence. The LLM does what it's best at, writing the outreach.

## 8. Limitations and next steps

- Franchise detection reads the company name and page title for known brands, and requires corroboration before trusting "locally/independently owned and operated". Two gaps remain: a franchise whose legal name carries no known brand and whose site is bot-walled is missed entirely (American Residential Services, in the run above), and an independent business that says "locally owned and operated" *and* names a franchise competitor on the same page will still be flagged. Next: treat franchise status as a reviewable flag rather than an automatic deduction.
- Regex extraction misses signals phrased unusually. Next: an LLM extraction pass over the about page, used only to fill gaps, with results stored as evidence.
- JavaScript-only websites return little HTML. Next: a Playwright fallback for pages with almost no text.
- Revenue isn't estimated here, since SaaSquatch already does it; a direct integration would pull it in.
- Enrichment runs in-process. Next: a job queue for multi-instance scale.
- Next integrations: push Shortlist leads straight to HubSpot/Salesforce via API, and a weekly "new A-tier leads" email digest.

## 9. Project structure

```
dealsieve/
├── backend/
│   ├── app/
│   │   ├── main.py        API routes, background enrichment, export
│   │   ├── ingest.py      CSV mapping, normalization, dedup
│   │   ├── scraper.py     async crawler, cache, robots.txt, retries
│   │   ├── extract.py     signals + evidence
│   │   ├── validate.py    email / phone validation
│   │   ├── scoring.py     acquisition fit model
│   │   ├── brief.py       outreach brief (AI + template)
│   │   ├── models.py      SQLAlchemy models
│   │   └── db.py          engine / sessions, SEED_DEMO startup seeding in main.py
│   ├── tests/
│   └── requirements.txt
├── frontend/src/          React app: App.jsx, components/ (Sidebar, StatCards, FilterBar,
│                          LeadTable, ScoreBar, LeadDrawer, IcpSettings…), styles.css
├── data/                  sample CSV, recorded demo websites, real-world test list
├── scripts/               demo data generator, reset_demo.sh / .ps1 (video helper)
├── Dockerfile, docker-compose.yml, render.yaml
└── .github/workflows/ci.yml
```
