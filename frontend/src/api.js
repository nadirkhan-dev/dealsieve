import { staticApi } from "./staticApi.js";

const BASE = import.meta.env.VITE_API_URL || "";

/* The GitHub Pages preview is built with VITE_STATIC=true and has no backend.
 * Every other build keeps the live API untouched. */
export const IS_STATIC = import.meta.env.VITE_STATIC === "true";

async function request(path, options = {}) {
  const res = await fetch(`${BASE}${path}`, {
    headers: options.body && !(options.body instanceof FormData) ? { "Content-Type": "application/json" } : {},
    ...options,
  });
  if (!res.ok) {
    let message = `Request failed (${res.status})`;
    try {
      const data = await res.json();
      message = typeof data.detail === "string" ? data.detail : message;
    } catch {}
    throw new Error(message);
  }
  return res.json();
}

export function toQuery(filters) {
  const params = new URLSearchParams();
  Object.entries(filters).forEach(([k, v]) => {
    if (v === "" || v === false || v == null || (Array.isArray(v) && v.length === 0)) return;
    params.set(k, Array.isArray(v) ? v.join(",") : v);
  });
  return params.toString();
}

const liveApi = {
  isStatic: false,
  stats: () => request("/api/stats"),
  leads: (filters) => request(`/api/leads?${toQuery(filters)}`),
  lead: (id) => request(`/api/leads/${id}`),
  updateLead: (id, body) => request(`/api/leads/${id}`, { method: "PATCH", body: JSON.stringify(body) }),
  brief: (id) => request(`/api/leads/${id}/brief`, { method: "POST" }),
  importFile: (file) => {
    const form = new FormData();
    form.append("file", file);
    return request("/api/leads/import", { method: "POST", body: form });
  },
  importSample: () => request("/api/leads/import-sample", { method: "POST" }),
  enrich: (body = {}) => request("/api/enrich", { method: "POST", body: JSON.stringify(body) }),
  job: (id) => request(`/api/jobs/${id}`),
  settings: () => request("/api/settings"),
  saveSettings: (body) => request("/api/settings", { method: "PUT", body: JSON.stringify(body) }),
  clear: () => request("/api/leads", { method: "DELETE" }),
  exportUrl: (filters) => `${BASE}/api/export.csv?${toQuery(filters)}`,
  download: (filters) => { window.location.href = liveApi.exportUrl(filters); },
};

export const api = IS_STATIC ? staticApi : liveApi;
