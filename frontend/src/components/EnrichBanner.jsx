export default function EnrichBanner({ stats, job, report, onStart, onDismissReport }) {
  const running = job && job.status === "running";
  const pct = job && job.total ? Math.round((job.done / job.total) * 100) : 0;

  return (
    <div className="banners">
      {report && (
        <div className="notice">
          <p>
            Imported <strong>{report.added}</strong> new leads from {report.rows_read} rows.
            {report.duplicates_in_file > 0 && <> Merged {report.duplicates_in_file} duplicate{report.duplicates_in_file === 1 ? "" : "s"}.</>}
            {report.already_in_pipeline > 0 && <> {report.already_in_pipeline} were already in your list and were updated.</>}
            {report.skipped_missing_name > 0 && <> Skipped {report.skipped_missing_name} row{report.skipped_missing_name === 1 ? "" : "s"} with no company name.</>}
          </p>
          <button className="link-btn" onClick={onDismissReport} aria-label="Dismiss import summary">Dismiss</button>
        </div>
      )}

      {running ? (
        <div className="progress-card" aria-live="polite">
          <div className="progress-head">
            <p>Reading company websites… {job.done} of {job.total}</p>
            {job.failed > 0 && <p className="muted">{job.failed} couldn't be reached</p>}
          </div>
          <div className="progress-track"><div className="progress-fill" style={{ width: `${pct}%` }} /></div>
          <p className="muted small">Scores appear in the table as each lead finishes. You can keep working.</p>
        </div>
      ) : stats.pending > 0 ? (
        <div className="cta-card">
          <div>
            <p className="cta-title">{stats.pending} leads haven't been scored yet</p>
            <p className="muted">DealSieve visits each website's home, about, services, contact and careers pages. Results are cached for 3 days.</p>
          </div>
          <button className="btn btn-primary" onClick={onStart}>Score {stats.pending} leads</button>
        </div>
      ) : null}
    </div>
  );
}
