import { useEffect, useState } from "react";
import { api } from "../api.js";

const WEIGHT_LABELS = {
  maturity: "Years in business",
  size: "Company size",
  industry: "Industry fit",
  recurring: "Recurring revenue",
  succession: "Owner transition",
  upside: "Digital upside",
  reachability: "Owner reachable",
};

export default function IcpSettings({ onClose, onSaved }) {
  const [icp, setIcp] = useState(null);
  const [industries, setIndustries] = useState("");
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState(null);

  useEffect(() => {
    api.settings().then((s) => { setIcp(s); setIndustries(s.target_industries.join(", ")); });
    const onKey = (e) => e.key === "Escape" && onClose();
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, []); // eslint-disable-line react-hooks/exhaustive-deps

  if (!icp) return null;
  const total = Object.values(icp.weights).reduce((a, b) => a + b, 0) || 1;
  const setWeight = (k, v) => setIcp((s) => ({ ...s, weights: { ...s.weights, [k]: v } }));

  async function save() {
    setSaving(true);
    setError(null);
    try {
      await api.saveSettings({ ...icp, target_industries: industries.split(",").map((s) => s.trim()).filter(Boolean) });
      onSaved();
    } catch (e) {
      setError(e.message);
      setSaving(false);
    }
  }

  return (
    <div className="drawer-scrim modal-scrim" onClick={onClose}>
      <div className="modal" role="dialog" aria-modal="true" aria-labelledby="settings-title" onClick={(e) => e.stopPropagation()}>
        <div className="drawer-head">
          <div>
            <h2 id="settings-title">Scoring settings</h2>
            <p className="muted">Describe the business you want to buy. Every lead is rescored instantly, without visiting websites again.</p>
          </div>
          <button className="icon-btn" onClick={onClose} aria-label="Close">×</button>
        </div>

        <label className="field">
          <span className="field-label">Target industries (comma separated)</span>
          <textarea rows="2" value={industries} onChange={(e) => setIndustries(e.target.value)} />
        </label>

        <div className="field-row">
          <label className="field">
            <span className="field-label">Min employees</span>
            <input type="number" min="0" value={icp.employees_min} onChange={(e) => setIcp({ ...icp, employees_min: Number(e.target.value) })} />
          </label>
          <label className="field">
            <span className="field-label">Max employees</span>
            <input type="number" min="1" value={icp.employees_max} onChange={(e) => setIcp({ ...icp, employees_max: Number(e.target.value) })} />
          </label>
          <label className="field">
            <span className="field-label">Min years in business</span>
            <input type="number" min="0" value={icp.min_years} onChange={(e) => setIcp({ ...icp, min_years: Number(e.target.value) })} />
          </label>
        </div>

        <p className="field-label">How much each factor matters</p>
        <div className="weights">
          {Object.entries(WEIGHT_LABELS).map(([k, label]) => (
            <label key={k} className="weight">
              <span>{label}</span>
              <input type="range" min="0" max="30" value={icp.weights[k]} onChange={(e) => setWeight(k, Number(e.target.value))} />
              <span className="weight-pct">{Math.round((icp.weights[k] / total) * 100)}%</span>
            </label>
          ))}
        </div>

        {error && <p className="field-error" role="alert">{error}</p>}
        <div className="modal-actions">
          <button className="btn btn-quiet" onClick={onClose}>Cancel</button>
          <button className="btn btn-primary" onClick={save} disabled={saving}>{saving ? "Rescoring…" : "Save and rescore"}</button>
        </div>
      </div>
    </div>
  );
}
