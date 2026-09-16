import { TIERS } from "../constants.js";
import { IconDownload, IconSearch, IconSliders } from "./Icons.jsx";

export default function FilterBar({ title, count, filters, setFilters, stats, onReset, onSettings, onExport, canExport }) {
  const set = (patch) => setFilters((f) => ({ ...f, ...patch }));
  const toggleTier = (t) => setFilters((f) => ({ ...f, tiers: f.tiers.includes(t) ? f.tiers.filter((x) => x !== t) : [...f.tiers, t] }));
  const active = filters.q || filters.tiers.length || filters.min_score || filters.industry || filters.has_email || filters.succession;

  return (
    <div className="panel-head">
      <div className="panel-title-row">
        <div>
          <h2 className="panel-title">{title}</h2>
          <p className="muted small">{count} {count === 1 ? "company" : "companies"}, highest fit first</p>
        </div>
        <div className="panel-tools">
          <label className="search">
            <IconSearch />
            <input type="search" placeholder="Search companies" aria-label="Search companies" value={filters.q} onChange={(e) => set({ q: e.target.value })} />
          </label>
          <button className="tool-btn" onClick={onSettings} title="Scoring settings" aria-label="Scoring settings"><IconSliders /></button>
          <button className="btn btn-primary" onClick={onExport} disabled={!canExport}><IconDownload /> Export CSV</button>
        </div>
      </div>

      <div className="filter-row" role="group" aria-label="Filters">
        <div className="chip-group" aria-label="Fit">
          {Object.entries(TIERS).map(([t, meta]) => (
            <button key={t} className={`chip ${filters.tiers.includes(t) ? "is-on" : ""}`} aria-pressed={filters.tiers.includes(t)} onClick={() => toggleTier(t)}>
              <span className={`tier-dot ${meta.className}`} aria-hidden="true" />
              {meta.label}
              <span className="chip-count">{stats.tiers[t]}</span>
            </button>
          ))}
        </div>

        <select className="select-sm" aria-label="Minimum score" value={filters.min_score} onChange={(e) => set({ min_score: Number(e.target.value) })}>
          <option value={0}>Any score</option>
          {[40, 55, 72, 85].map((n) => <option key={n} value={n}>Score {n}+</option>)}
        </select>

        {stats.industries.length > 0 && (
          <select className="select-sm" aria-label="Industry" value={filters.industry} onChange={(e) => set({ industry: e.target.value })}>
            <option value="">All industries</option>
            {stats.industries.map((i) => <option key={i} value={i}>{i}</option>)}
          </select>
        )}

        {active ? <button className="link-btn" onClick={onReset}>Clear filters</button> : null}
      </div>
    </div>
  );
}
