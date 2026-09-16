import { useRef, useState } from "react";

export default function ImportPanel({ onImport }) {
  const inputRef = useRef(null);
  const [dragging, setDragging] = useState(false);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState(null);

  async function run(fileOrSample) {
    setBusy(true);
    setError(null);
    try {
      await onImport(fileOrSample);
    } catch (e) {
      setError(e.message);
    } finally {
      setBusy(false);
    }
  }

  return (
    <section className="import">
      <div className="import-copy">
        <h1>Find the leads <span className="gradient-text">worth acquiring</span></h1>
        <p>
          Drop in a lead export from SaaSquatch Leads or your CRM. DealSieve reads each company's website and ranks
          every lead on acquisition fit: how long it has been around, whether it earns recurring revenue, whether
          the owner may be ready to step back, and whether you can reach them.
        </p>
        <ul className="import-points">
          <li>
            <span className="icon-tile tile-teal" aria-hidden="true">
              <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round"><path d="M4 19V5M4 19h16M8 15l3-4 3 2 5-6" /></svg>
            </span>
            <div><strong>Explainable fit scores</strong><span className="muted">Every score shows the sentence on the website it came from.</span></div>
          </li>
          <li>
            <span className="icon-tile tile-blue" aria-hidden="true">
              <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round"><path d="M20 6 9 17l-5-5" /></svg>
            </span>
            <div><strong>Clean, verified data</strong><span className="muted">Duplicates are merged and emails are checked before you export.</span></div>
          </li>
          <li>
            <span className="icon-tile tile-violet" aria-hidden="true">
              <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round"><path d="M12 3v12m0 0-4-4m4 4 4-4M5 21h14" /></svg>
            </span>
            <div><strong>Ready for your CRM</strong><span className="muted">Exports map straight into HubSpot or Salesforce.</span></div>
          </li>
        </ul>
      </div>

      <div
        className={`dropzone ${dragging ? "is-dragging" : ""}`}
        onDragOver={(e) => { e.preventDefault(); setDragging(true); }}
        onDragLeave={() => setDragging(false)}
        onDrop={(e) => { e.preventDefault(); setDragging(false); if (e.dataTransfer.files[0]) run(e.dataTransfer.files[0]); }}
      >
        <p className="dropzone-title">Drop a CSV file here</p>
        <p className="dropzone-hint">Needs a company name column. Website, industry, city, employees, owner, email and phone are used when present.</p>
        <input ref={inputRef} type="file" accept=".csv,text/csv" hidden onChange={(e) => e.target.files[0] && run(e.target.files[0])} />
        <div className="dropzone-actions">
          <button className="btn btn-primary" disabled={busy} onClick={() => inputRef.current.click()}>
            {busy ? "Importing…" : "Choose CSV file"}
          </button>
          <button className="btn btn-quiet" disabled={busy} onClick={() => run("sample")}>Try with sample leads</button>
        </div>
        {error && <p className="field-error" role="alert">{error}</p>}
      </div>
    </section>
  );
}
