# 2-minute video script

Record your screen with the app open. Speak naturally; don't read word for word.

**0:00–0:15 — The problem**
"SaaSquatch is great at finding businesses. But most of its users are searchers trying to acquire a company, and for them the hard part isn't finding 500 leads, it's knowing which 20 are worth calling. So I built DealSieve: acquisition-fit scoring for SaaSquatch leads."

**0:15–0:35 — Import** (click "Try with sample leads")
"I drop in an export. Columns are mapped automatically, and duplicates like 'Reyes Comfort Heating & Air' and the same company with 'LLC' are merged. Re-importing adds nothing."

**0:35–1:05 — Enrich and score** (click "Score 13 leads", then open Reyes Comfort)
"The crawler reads each company's home, about, services and contact pages. It respects robots.txt, caches responses, and flags bot-protected sites instead of bypassing them. Each score is split into three questions: is it a solid business, is there an opportunity, can I reach the owner. And every signal shows the sentence it came from. Here it found 35 years in business, a maintenance plan, and the owner thinking about his next chapter."

**1:05–1:25 — Risks and buy box** (point to Keystone's Risk tag, open Scoring settings, drag a weight)
"A good-looking company that's already PE-backed gets penalized. Every searcher has a different buy box, so I can change industries, size and weights, and everything rescores instantly without re-crawling."

**1:25–1:45 — Action** (Write outreach brief, set stage to Shortlist, Export)
"From here I generate an owner brief with first-call questions and a respectful first email, move the lead to my shortlist, and export a CSV that maps straight into HubSpot."

**1:45–2:00 — Architecture**
"It's FastAPI with async crawling, SQLAlchemy on Postgres, a React front end, all in one Docker container on Cloud Run. The score is rules-based so it's explainable, and AI is used where it's strongest: writing. Thanks for watching."
