import { useCallback, useEffect, useRef, useState } from "react";
import { api, IS_STATIC } from "./api.js";
import { NEEDS_SERVER } from "./staticApi.js";
import StaticBanner from "./components/StaticBanner.jsx";
import { STAGES } from "./constants.js";
import StepBar from "./components/StepBar.jsx";
import ImportPanel from "./components/ImportPanel.jsx";
import Sidebar from "./components/Sidebar.jsx";
import StatCards from "./components/StatCards.jsx";
import FilterBar from "./components/FilterBar.jsx";
import LeadTable from "./components/LeadTable.jsx";
import LeadDrawer from "./components/LeadDrawer.jsx";
import IcpSettings from "./components/IcpSettings.jsx";
import EnrichBanner from "./components/EnrichBanner.jsx";

const EMPTY_FILTERS = { q: "", tiers: [], min_score: 0, industry: "", stage: [], has_email: false, succession: false, sort: "score", order: "desc" };

export default function App() {
  const [stats, setStats] = useState(null);
  const [leads, setLeads] = useState([]);
  const [filters, setFilters] = useState(EMPTY_FILTERS);
  const [selectedId, setSelectedId] = useState(null);
  const [job, setJob] = useState(null);
  const [importReport, setImportReport] = useState(null);
  const [showSettings, setShowSettings] = useState(false);
  const [error, setError] = useState(null);
  const [exported, setExported] = useState(false);
  const [blocked, setBlocked] = useState(null);
  const pollRef = useRef(null);
  const fileRef = useRef(null);

  const refresh = useCallback(async (f = filters) => {
    try {
      const [s, l] = await Promise.all([api.stats(), api.leads(f)]);
      setStats(s);
      setLeads(l.items);
      setError(null);
    } catch (e) {
      setError(IS_STATIC
        ? `Could not load the pre-computed demo data. (${e.message})`
        : `Can't reach the API. Start the backend on port 8000 and reload. (${e.message})`);
    }
  }, [filters]);

  useEffect(() => {
    const t = setTimeout(() => refresh(filters), filters.q ? 200 : 0);
    return () => clearTimeout(t);
  }, [filters]); // eslint-disable-line react-hooks/exhaustive-deps

  useEffect(() => () => clearInterval(pollRef.current), []);

  function blockIfStatic() {
    if (!IS_STATIC) return false;
    setBlocked(NEEDS_SERVER);
    return true;
  }

  async function handleImport(fileOrSample) {
    if (blockIfStatic()) return null;
    const report = fileOrSample === "sample" ? await api.importSample() : await api.importFile(fileOrSample);
    setImportReport(report);
    await refresh();
    return report;
  }

  async function startEnrichment(body = {}) {
    if (blockIfStatic()) return;
    const started = await api.enrich(body);
    if (!started.total) return;
    setJob({ id: started.job_id, total: started.total, done: 0, failed: 0, status: "running" });
    clearInterval(pollRef.current);
    pollRef.current = setInterval(async () => {
      const j = await api.job(started.job_id);
      setJob(j);
      refresh();
      if (j.status === "finished") clearInterval(pollRef.current);
    }, 900);
  }

  async function handleClear() {
    if (blockIfStatic()) return;
    if (!window.confirm("Remove all leads from DealSieve? This can't be undone.")) return;
    await api.clear();
    setImportReport(null);
    setSelectedId(null);
    setFilters(EMPTY_FILTERS);
    refresh(EMPTY_FILTERS);
  }

  function handleExport() {
    api.download(filters);
    setExported(true);
  }

  const hasLeads = stats && stats.total > 0;
  const reviewed = stats ? stats.enriched + stats.failed : 0;
  const step = !hasLeads ? 1 : stats.pending > 0 ? 2 : exported ? 4 : 3;
  const activeStage = filters.stage[0] || "";
  const stageLabel = STAGES.find((s) => s.value === activeStage)?.label;

  return (
    <div className="shell">
      <Sidebar
        stats={stats}
        activeStage={activeStage}
        onStage={(stage) => setFilters((f) => ({ ...f, stage: stage ? [stage] : [] }))}
        onImport={() => (IS_STATIC ? setBlocked(NEEDS_SERVER) : fileRef.current.click())}
        onSettings={() => setShowSettings(true)}
        onClear={handleClear}
      />
      <input ref={fileRef} type="file" accept=".csv,text/csv" hidden onChange={(e) => { if (e.target.files[0]) handleImport(e.target.files[0]).catch((err) => setError(err.message)); e.target.value = ""; }} />

      <div className="content">
        <header className="page-head">
          <div>
            <h1 className="page-title">Acquisition Fit</h1>
            <p className="muted">Rank your leads by how good they'd be to buy, not just to sell to.</p>
          </div>
          <StepBar current={step} />
        </header>

        {IS_STATIC && <StaticBanner />}
        {error && <div className="alert alert-risk" role="alert">{error}</div>}
        {blocked && (
          <div className="alert alert-info" role="status">
            {blocked} <button className="link-btn" onClick={() => setBlocked(null)}>Dismiss</button>
          </div>
        )}
        {!IS_STATIC && stats?.demo_mode && hasLeads && (
          <div className="alert alert-info">Demo mode: websites come from recorded pages in <code>data/demo_sites.json</code>. Set <code>DEMO_MODE=false</code> to read live sites.</div>
        )}

        {!hasLeads ? (
          stats && <ImportPanel onImport={handleImport} />
        ) : (
          <>
            <EnrichBanner stats={stats} job={job} report={importReport} onStart={() => startEnrichment()} onDismissReport={() => setImportReport(null)} />
            <StatCards stats={stats} filters={filters} setFilters={setFilters} />
            <section className="panel">
              <FilterBar
                title={stageLabel ? `${stageLabel} leads` : "All leads"}
                count={leads.length}
                filters={filters}
                setFilters={setFilters}
                stats={stats}
                onReset={() => setFilters((f) => ({ ...EMPTY_FILTERS, stage: f.stage }))}
                onSettings={() => setShowSettings(true)}
                onExport={handleExport}
                canExport={reviewed > 0 && leads.length > 0}
              />
              <LeadTable
                leads={leads}
                filters={filters}
                setFilters={setFilters}
                selectedId={selectedId}
                onSelect={setSelectedId}
                onStageChange={async (id, stage) => { await api.updateLead(id, { stage }); refresh(); }}
              />
            </section>
          </>
        )}
      </div>

      {selectedId && (
        <LeadDrawer
          id={selectedId}
          onClose={() => setSelectedId(null)}
          onChanged={refresh}
          onRecrawl={(id) => startEnrichment({ lead_ids: [id], force: true })}
          aiEnabled={stats?.ai_briefs}
        />
      )}
      {showSettings && <IcpSettings onClose={() => setShowSettings(false)} onSaved={() => { setShowSettings(false); refresh(); }} />}
    </div>
  );
}
