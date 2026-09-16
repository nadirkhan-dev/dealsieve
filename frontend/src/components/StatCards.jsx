import { IconCheckCircle, IconHandshake, IconMail, IconUsers } from "./Icons.jsx";

// Each card is also a filter, so the overview doubles as the fastest way to narrow the list.
export default function StatCards({ stats, filters, setFilters }) {
  const cards = [
    { key: "all", label: "Leads scored", value: stats.enriched + stats.failed, sub: `of ${stats.total} imported`, icon: IconUsers, tone: "blue",
      active: !filters.tiers.length && !filters.succession && !filters.has_email,
      apply: (f) => ({ ...f, tiers: [], succession: false, has_email: false }) },
    { key: "fit", label: "Strong fit", value: stats.tiers.A, sub: "score 72 or higher", icon: IconCheckCircle, tone: "teal",
      active: filters.tiers.length === 1 && filters.tiers[0] === "A",
      apply: (f) => ({ ...f, tiers: f.tiers.length === 1 && f.tiers[0] === "A" ? [] : ["A"] }) },
    { key: "transition", label: "Owner transition", value: stats.signals.owner_transition, sub: "retiring or family-run", icon: IconHandshake, tone: "violet",
      active: filters.succession, apply: (f) => ({ ...f, succession: !f.succession }) },
    { key: "email", label: "Direct owner email", value: stats.signals.direct_email, sub: "ready for outreach", icon: IconMail, tone: "amber",
      active: filters.has_email, apply: (f) => ({ ...f, has_email: !f.has_email }) },
  ];
  return (
    <div className="stat-cards">
      {cards.map(({ key, label, value, sub, icon: Icon, tone, active, apply }) => (
        <button key={key} className={`stat ${active ? "is-active" : ""}`} aria-pressed={active} onClick={() => setFilters(apply)}>
          <span className={`icon-tile tile-${tone}`}><Icon /></span>
          <span className="stat-text">
            <span className="stat-label">{label}</span>
            <span className="stat-value">{value}</span>
            <span className="stat-sub">{sub}</span>
          </span>
        </button>
      ))}
    </div>
  );
}
