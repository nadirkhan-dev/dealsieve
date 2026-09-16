import { EMAIL_STATUS, SIGNAL_TAGS, STAGES, TIERS } from "../constants.js";
import ScoreBar from "./ScoreBar.jsx";

function SortHeader({ label, field, filters, setFilters, className = "" }) {
  const active = filters.sort === field;
  const next = active && filters.order === "desc" ? "asc" : "desc";
  return (
    <th className={className} aria-sort={active ? (filters.order === "desc" ? "descending" : "ascending") : "none"}>
      <button className="th-btn" onClick={() => setFilters((f) => ({ ...f, sort: field, order: next }))}>
        {label}{active && <span aria-hidden="true">{filters.order === "desc" ? " ↓" : " ↑"}</span>}
      </button>
    </th>
  );
}

export default function LeadTable({ leads, filters, setFilters, selectedId, onSelect, onStageChange }) {
  if (!leads.length) {
    return (
      <div className="empty">
        <p className="empty-title">No leads match these filters</p>
        <p className="muted">Lower the minimum score, pick another stage, or clear filters to see more.</p>
      </div>
    );
  }

  return (
    <div className="table-wrap">
      <table className="leads">
        <thead>
          <tr>
            <SortHeader label="Company" field="name" filters={filters} setFilters={setFilters} />
            <SortHeader label="Acquisition fit" field="score" filters={filters} setFilters={setFilters} className="col-fit" />
            <SortHeader label="Years" field="years" filters={filters} setFilters={setFilters} className="col-num" />
            <th className="col-num">Staff</th>
            <th>Signals</th>
            <th>Contact</th>
            <th>Stage</th>
          </tr>
        </thead>
        <tbody>
          {leads.map((l) => {
            const pending = l.status === "pending";
            const lowData = !pending && l.confidence < 50;
            const email = EMAIL_STATUS[l.email_status];
            const tags = Object.entries(l.tags).filter(([, v]) => v).map(([k]) => SIGNAL_TAGS[k]);
            return (
              <tr
                key={l.id}
                className={selectedId === l.id ? "is-selected" : ""}
                onClick={() => onSelect(l.id)}
                onKeyDown={(e) => { if (e.key === "Enter") onSelect(l.id); }}
                tabIndex={0}
                aria-label={`Open ${l.name}`}
              >
                <td>
                  <p className="co-name">{l.name}</p>
                  <p className="co-meta">{[l.city, l.state].filter(Boolean).join(", ")}{l.industry ? ` — ${l.industry}` : ""}</p>
                </td>
                <td className="col-fit">
                  <div className="fit">
                    <span className={`score ${pending ? "score-pending" : TIERS[l.tier].className}`}>{pending ? "–" : l.score}</span>
                    <div className="fit-detail">
                      <ScoreBar breakdown={l.breakdown} pending={pending} />
                      <p className="fit-label">
                        {pending ? "Not scored yet" : lowData ? "Needs manual review" : TIERS[l.tier].label}
                      </p>
                    </div>
                  </div>
                </td>
                <td className="col-num">{l.years_in_business ?? "—"}</td>
                <td className="col-num">{l.employees ?? "—"}</td>
                <td>
                  <div className="tags">
                    {tags.length ? tags.map((t) => <span key={t} className="tag">{t}</span>) : <span className="muted small">—</span>}
                    {l.flags.some((f) => f.level === "risk") && <span className="tag tag-risk">Risk</span>}
                  </div>
                </td>
                <td>
                  {email ? <span className={`status status-${email.tone}`}>{email.label}</span> : <span className="muted small">No email</span>}
                </td>
                <td onClick={(e) => e.stopPropagation()}>
                  <select className="stage-select" value={l.stage} aria-label={`Stage for ${l.name}`} onChange={(e) => onStageChange(l.id, e.target.value)}>
                    {STAGES.map((s) => <option key={s.value} value={s.value}>{s.label}</option>)}
                  </select>
                </td>
              </tr>
            );
          })}
        </tbody>
      </table>
      <div className="legend" aria-hidden="true">
        <span><i className="seg-business" /> Solid business</span>
        <span><i className="seg-opportunity" /> Opportunity</span>
        <span><i className="seg-access" /> Owner reachable</span>
        <span><i className="seg-unknown-key" /> Estimated, not found on site</span>
      </div>
    </div>
  );
}
