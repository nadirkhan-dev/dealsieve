import { IconArrowLeft, IconGauge, IconSend, IconSliders, IconStar, IconTrash, IconUpload, IconX } from "./Icons.jsx";

const PIPELINE = [
  { stage: "", label: "All leads", icon: IconGauge, count: (s) => s.total },
  { stage: "shortlist", label: "Shortlist", icon: IconStar, count: (s) => s.stages.shortlist },
  { stage: "contacted", label: "Contacted", icon: IconSend, count: (s) => s.stages.contacted },
  { stage: "passed", label: "Passed", icon: IconX, count: (s) => s.stages.passed },
];

export default function Sidebar({ stats, activeStage, onStage, onImport, onSettings, onClear }) {
  const hasLeads = stats && stats.total > 0;
  return (
    <aside className="sidebar">
      <div className="sb-brand">
        <span className="brand-mark" aria-hidden="true" />
        <div>
          <p className="brand-name">DealSieve</p>
          <p className="brand-sub">for SaaSquatch Leads</p>
        </div>
      </div>

      <nav aria-label="Main">
        <p className="sb-heading">Acquisition pipeline</p>
        {PIPELINE.map(({ stage, label, icon: Icon, count }) => (
          <button
            key={label}
            className={`sb-item ${activeStage === stage ? "is-active" : ""}`}
            onClick={() => onStage(stage)}
            disabled={!hasLeads}
            aria-current={activeStage === stage ? "page" : undefined}
          >
            <Icon />
            <span>{label}</span>
            {hasLeads && <span className="sb-count">{count(stats)}</span>}
          </button>
        ))}

        <p className="sb-heading">Tools</p>
        <button className="sb-item" onClick={onImport}><IconUpload /><span>Import leads</span></button>
        <button className="sb-item" onClick={onSettings} disabled={!hasLeads}><IconSliders /><span>Scoring settings</span></button>
        {hasLeads && <button className="sb-item sb-danger" onClick={onClear}><IconTrash /><span>Remove all leads</span></button>}
      </nav>

      <a className="sb-back" href="https://www.saasquatchleads.com" target="_blank" rel="noreferrer">
        <IconArrowLeft /><span>Back to SaaSquatch Leads</span>
      </a>
    </aside>
  );
}
