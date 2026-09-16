import { useEffect, useState } from "react";
import { api } from "../api.js";
import { COMPONENT_GROUPS, EMAIL_STATUS, GROUP_LABELS, PAGE_NAMES, STAGES, TIERS } from "../constants.js";

const EVIDENCE_LABELS = {
  founded_year: "Founding year",
  owner_name: "Owner",
  succession: "Owner transition",
  family_owned: "Family business",
  recurring_revenue: "Recurring revenue",
  hiring: "Hiring",
  franchise: "Franchise",
  pe_backed: "Existing investor",
};

function CopyButton({ text, label = "Copy" }) {
  const [done, setDone] = useState(false);
  return (
    <button className="link-btn" onClick={async () => { await navigator.clipboard.writeText(text); setDone(true); setTimeout(() => setDone(false), 1500); }}>
      {done ? "Copied" : label}
    </button>
  );
}

export default function LeadDrawer({ id, onClose, onChanged, onRecrawl, aiEnabled }) {
  const [lead, setLead] = useState(null);
  const [notes, setNotes] = useState("");
  const [briefBusy, setBriefBusy] = useState(false);
  const [briefError, setBriefError] = useState(null);

  useEffect(() => {
    let alive = true;
    api.lead(id).then((l) => { if (alive) { setLead(l); setNotes(l.notes || ""); } });
    const load = () => api.lead(id).then((l) => alive && setLead(l));
    const t = setInterval(load, 3000); // picks up a re-crawl finishing
    const onKey = (e) => e.key === "Escape" && onClose();
    window.addEventListener("keydown", onKey);
    return () => { alive = false; clearInterval(t); window.removeEventListener("keydown", onKey); };
  }, [id]); // eslint-disable-line react-hooks/exhaustive-deps

  if (!lead) return <div className="drawer-scrim" onClick={onClose}><aside className="drawer" /></div>;

  const s = lead.signals || {};
  const pending = lead.status === "pending";
  const tier = TIERS[lead.tier];
  const email = EMAIL_STATUS[lead.email_status];
  const groups = Object.keys(GROUP_LABELS).map((g) => ({ g, rows: lead.breakdown.filter((b) => COMPONENT_GROUPS[b.key] === g) }));
  const evidence = Object.entries(s.evidence || {}).filter(([k]) => EVIDENCE_LABELS[k]);

  async function saveStage(stage) {
    setLead(await api.updateLead(lead.id, { stage }));
    onChanged();
  }
  async function saveNotes() {
    if (notes === (lead.notes || "")) return;
    setLead(await api.updateLead(lead.id, { notes }));
  }
  async function writeBrief() {
    setBriefBusy(true);
    setBriefError(null);
    try {
      const brief = await api.brief(lead.id);
      setLead((l) => ({ ...l, brief }));
    } catch (e) {
      setBriefError(e.message);
    } finally {
      setBriefBusy(false);
    }
  }

  return (
    <div className="drawer-scrim" onClick={onClose}>
      <aside className="drawer" role="dialog" aria-modal="true" aria-labelledby="drawer-title" onClick={(e) => e.stopPropagation()}>
        <div className="drawer-head">
          <div>
            <h2 id="drawer-title">{lead.name}</h2>
            <p className="muted">
              {[lead.city, lead.state].filter(Boolean).join(", ")}
              {lead.domain && <> — <a href={`https://${lead.domain}`} target="_blank" rel="noreferrer">{lead.domain}</a></>}
            </p>
          </div>
          <button className="icon-btn" onClick={onClose} aria-label="Close">×</button>
        </div>

        <section className="drawer-score">
          <span className={`score score-lg ${pending ? "score-pending" : tier.className}`}>{pending ? "–" : lead.score}</span>
          <div>
            <p className="drawer-tier">{pending ? "Not scored yet" : tier.label}</p>
            <p className="muted small">
              {pending ? "Run scoring to read this company's website." : `Based on ${lead.confidence}% of signals found on the website`}
            </p>
          </div>
          {!pending && lead.domain && <button className="btn btn-quiet btn-sm" onClick={() => onRecrawl(lead.id)}>Re-check website</button>}
        </section>

        {lead.flags.length > 0 && (
          <ul className="flags">
            {lead.flags.map((f) => <li key={f.text} className={`flag flag-${f.level}`}>{f.text}</li>)}
          </ul>
        )}

        {!pending && (
          <section className="drawer-section">
            <h3>Why this score</h3>
            {groups.map(({ g, rows }) => (
              <div key={g} className="group">
                <p className="group-label">{GROUP_LABELS[g]}</p>
                {rows.map((b) => (
                  <div key={b.key} className="brk">
                    <div className="brk-top">
                      <span>{b.label}</span>
                      <span className="brk-pts">{Math.round(b.points)} / {Math.round(b.max)}</span>
                    </div>
                    <div className="brk-track"><div className={`brk-fill seg-${g} ${b.known ? "" : "seg-unknown"}`} style={{ width: `${b.ratio * 100}%` }} /></div>
                    <p className={`brk-reason ${b.known ? "" : "muted"}`}>{b.reason}</p>
                  </div>
                ))}
              </div>
            ))}
          </section>
        )}

        {evidence.length > 0 && (
          <section className="drawer-section">
            <h3>Found on their website</h3>
            {evidence.map(([k, ev]) => (
              <figure key={k} className="evidence">
                <blockquote>{ev.text}</blockquote>
                <figcaption>{EVIDENCE_LABELS[k]}, from the {PAGE_NAMES[ev.page]?.toLowerCase() || ev.page}</figcaption>
              </figure>
            ))}
          </section>
        )}

        <section className="drawer-section">
          <h3>Contact</h3>
          <dl className="contact">
            <dt>Owner</dt><dd>{lead.owner_name || <span className="muted">Not found</span>}</dd>
            <dt>Email</dt>
            <dd>
              {lead.email ? <>{lead.email} {email && <span className={`status status-${email.tone}`}>{email.label}</span>} <CopyButton text={lead.email} /></> : <span className="muted">Not found</span>}
            </dd>
            <dt>Phone</dt><dd>{lead.phone ? <>{lead.phone} <CopyButton text={lead.phone} /></> : <span className="muted">Not found</span>}</dd>
            {s.socials?.linkedin && <><dt>LinkedIn</dt><dd><a href={s.socials.linkedin} target="_blank" rel="noreferrer">Company page</a></dd></>}
          </dl>
        </section>

        <section className="drawer-section">
          <h3>Pipeline</h3>
          <div className="segmented" role="radiogroup" aria-label="Pipeline stage">
            {STAGES.map((st) => (
              <button key={st.value} role="radio" aria-checked={lead.stage === st.value} className={lead.stage === st.value ? "is-on" : ""} onClick={() => saveStage(st.value)}>
                {st.label}
              </button>
            ))}
          </div>
          <label className="field">
            <span className="field-label">Notes</span>
            <textarea rows="3" value={notes} onChange={(e) => setNotes(e.target.value)} onBlur={saveNotes} placeholder="Saved when you click away" />
          </label>
        </section>

        <section className="drawer-section">
          <div className="section-row">
            <h3>Outreach brief</h3>
            {!pending && (
              <button className="btn btn-primary btn-sm" onClick={writeBrief} disabled={briefBusy}>
                {briefBusy ? "Writing…" : lead.brief ? "Rewrite brief" : "Write outreach brief"}
              </button>
            )}
          </div>
          {!lead.brief && !briefBusy && (
            <p className="muted small">
              A one-page summary, first-call questions and a first email to the owner, written only from what was found above.
              {!aiEnabled && " Add ANTHROPIC_API_KEY on the server for AI-written briefs; a template is used until then."}
            </p>
          )}
          {briefError && <p className="field-error">{briefError}</p>}
          {lead.brief && (
            <div className="brief">
              <p>{lead.brief.summary}</p>
              <p className="group-label">Why it fits</p>
              <ul>{lead.brief.why_it_fits.map((x) => <li key={x}>{x}</li>)}</ul>
              <p className="group-label">Watch out for</p>
              <ul>{lead.brief.risks.map((x) => <li key={x}>{x}</li>)}</ul>
              <p className="group-label">Ask on the first call</p>
              <ul>{lead.brief.questions.map((x) => <li key={x}>{x}</li>)}</ul>
              <div className="email">
                <div className="section-row">
                  <p className="email-subject">{lead.brief.email_subject}</p>
                  <CopyButton text={`Subject: ${lead.brief.email_subject}\n\n${lead.brief.email_body}`} label="Copy email" />
                </div>
                <pre>{lead.brief.email_body}</pre>
              </div>
              <p className="muted small">Written by {lead.brief.source.startsWith("ai") ? "AI" : lead.brief.source}. Check facts before sending.</p>
            </div>
          )}
        </section>
      </aside>
    </div>
  );
}
