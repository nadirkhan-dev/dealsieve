/* Static-preview data layer for the GitHub Pages build (VITE_STATIC=true).
 *
 * Reads the pre-computed snapshot.json instead of calling /api, and reproduces
 * the backend's filtering, sorting and CSV export in the browser so the
 * dashboard behaves the same offline. Stage and notes edits are kept in
 * localStorage, so the pipeline still feels live.
 *
 * Anything that genuinely needs a server -- importing a CSV, crawling, scoring,
 * saving the buy box -- rejects with NEEDS_SERVER, which the UI renders as an
 * inline message.
 */
const STORAGE_KEY = "dealsieve.static.edits";

export const NEEDS_SERVER = "Needs the full app. Run it locally with Docker (see README).";

/* localStorage is unavailable in some privacy modes, and throws rather than
 * returning null, so every access is guarded. */
function readEdits() {
  try {
    return JSON.parse(localStorage.getItem(STORAGE_KEY) || "{}") || {};
  } catch {
    return {};
  }
}

function writeEdits(edits) {
  try {
    localStorage.setItem(STORAGE_KEY, JSON.stringify(edits));
  } catch {
    /* preview still works for this session, the edit just will not persist */
  }
}

let snapshotPromise = null;

function loadSnapshot() {
  if (!snapshotPromise) {
    // import.meta.env.BASE_URL keeps this correct under the /dealsieve/ base path.
    snapshotPromise = fetch(`${import.meta.env.BASE_URL}snapshot.json`).then((res) => {
      if (!res.ok) throw new Error(`Could not load snapshot.json (${res.status})`);
      return res.json();
    });
  }
  return snapshotPromise;
}

/* Apply saved stage/notes edits on top of the immutable snapshot. */
function withEdits(lead, edits) {
  const edit = edits[String(lead.id)];
  return edit ? { ...lead, ...edit } : lead;
}

function parseList(value) {
  if (Array.isArray(value)) return value.filter(Boolean);
  if (typeof value === "string" && value) return value.split(",").map((v) => v.trim()).filter(Boolean);
  return [];
}

/* Mirrors filtered_query() in backend/app/main.py. */
export function applyFilters(leads, f = {}, rawIndustries = {}) {
  let out = leads;

  if (f.q) {
    const needle = String(f.q).toLowerCase();
    // The backend LIKEs name, domain and city; a NULL column never matches.
    out = out.filter((l) =>
      [l.name, l.domain, l.city].some((v) => v && String(v).toLowerCase().includes(needle)));
  }

  const tiers = parseList(f.tiers).map((t) => t.toUpperCase());
  if (tiers.length) out = out.filter((l) => tiers.includes(l.tier));

  if (f.min_score) out = out.filter((l) => (l.score ?? 0) >= Number(f.min_score));

  if (f.industry) {
    // The backend matches the raw industry column, not the guess from the site.
    const want = String(f.industry).toLowerCase();
    out = out.filter((l) => (rawIndustries[String(l.id)] || "").toLowerCase() === want);
  }

  const stages = parseList(f.stage);
  if (stages.length) out = out.filter((l) => stages.includes(l.stage));

  if (f.has_email) out = out.filter((l) => ["valid", "personal_domain"].includes(l.email_status));

  if (f.succession) out = out.filter((l) => l.tags?.succession || l.tags?.family_owned);

  if (f.status) out = out.filter((l) => l.status === f.status);

  return out;
}

/* Mirrors SORTS in backend/app/main.py. */
const SORTS = {
  score: (l) => [l.score ?? 0, l.confidence ?? 0],
  name: (l) => [String(l.name).toLowerCase()],
  years: (l) => [l.years_in_business ?? -1],
  confidence: (l) => [l.confidence ?? 0],
};

export function applySort(leads, sort = "score", order = "desc") {
  const key = SORTS[sort] || SORTS.score;
  const dir = order === "desc" ? -1 : 1;
  /* Compare in the requested direction rather than sorting ascending and
   * reversing. Array.prototype.sort is stable, like Python's list.sort, so
   * ties keep the incoming (id ascending) order instead of being flipped --
   * which is what the backend does. */
  return [...leads].sort((a, b) => {
    const ka = key(a);
    const kb = key(b);
    for (let i = 0; i < ka.length; i += 1) {
      if (ka[i] < kb[i]) return -1 * dir;
      if (ka[i] > kb[i]) return 1 * dir;
    }
    return 0;
  });
}

async function editedLeads() {
  const snap = await loadSnapshot();
  const edits = readEdits();
  /* Sort by id first: the backend filters rows in primary-key order and then
   * applies a stable sort, so tie order depends on this starting order. */
  const leads = snap.leads
    .map((l) => withEdits(l, edits))
    .sort((a, b) => a.id - b.id);
  return { snap, edits, leads };
}

/* ---- CSV export: same columns as /api/export.csv ------------------------- */
function csvCell(value) {
  const s = value == null ? "" : String(value);
  return /[",\n]/.test(s) ? `"${s.replace(/"/g, '""')}"` : s;
}

export function buildCsv(leads, details) {
  const header = ["Company name", "Company Domain Name", "First Name", "Last Name", "Email", "Phone Number",
    "City", "State/Region", "Industry", "Number of Employees", "Year Founded",
    "Acquisition Fit Score", "Fit Tier", "Data Confidence", "Email Status", "Why It Fits",
    "Risks", "Pipeline Stage", "Notes"];

  const rows = leads.map((l) => {
    const d = { ...(details[String(l.id)] || {}), ...l };
    const owner = d.owner_name || "";
    const space = owner.indexOf(" ");
    const first = space === -1 ? owner : owner.slice(0, space);
    const last = space === -1 ? "" : owner.slice(space + 1);
    const top = [...(d.breakdown || [])].sort((a, b) => b.points - a.points).slice(0, 3);
    return [d.name, d.domain || "", first, last, d.email || "", d.phone || "",
      d.city || "", d.state || "", d.industry || "", d.employees || "",
      (d.signals || {}).founded_year || "", d.score, d.tier, `${d.confidence}%`,
      d.email_status || "", top.map((b) => b.reason).join("; "),
      (d.flags || []).filter((f) => f.level !== "good").map((f) => f.text).join("; "),
      d.stage, d.notes || ""];
  });

  return [header, ...rows].map((r) => r.map(csvCell).join(",")).join("\r\n");
}

const rejectServer = () => Promise.reject(new Error(NEEDS_SERVER));

export const staticApi = {
  isStatic: true,

  async stats() {
    const { snap, leads } = await editedLeads();
    // Stage counts are recomputed so the sidebar reacts to pipeline edits.
    const stages = { new: 0, shortlist: 0, contacted: 0, passed: 0 };
    leads.forEach((l) => { if (l.stage in stages) stages[l.stage] += 1; });
    return { ...snap.stats, stages };
  },

  async leads(filters = {}) {
    const { snap, leads } = await editedLeads();
    const matched = applyFilters(leads, filters, snap.raw_industries);
    const sorted = applySort(matched, filters.sort, filters.order);
    return { items: sorted, count: sorted.length };
  },

  async lead(id) {
    const { snap, edits } = await editedLeads();
    const detail = snap.details[String(id)];
    if (!detail) throw new Error("Lead not found");
    return withEdits(detail, edits);
  },

  async updateLead(id, body) {
    const edits = readEdits();
    const key = String(id);
    edits[key] = { ...(edits[key] || {}), ...body };
    writeEdits(edits);
    return this.lead(id);
  },

  /* The brief was generated at build time, so this just returns it. */
  async brief(id) {
    const detail = await this.lead(id);
    if (!detail.brief) throw new Error(NEEDS_SERVER);
    return detail.brief;
  },

  async settings() {
    return (await loadSnapshot()).settings;
  },

  async download(filters = {}) {
    const { snap, leads } = await editedLeads();
    const matched = applyFilters(leads, filters, snap.raw_industries);
    // /api/export.csv always sorts by score, regardless of the table's sort.
    const csv = buildCsv(applySort(matched, "score", "desc"), snap.details);
    const url = URL.createObjectURL(new Blob([csv], { type: "text/csv;charset=utf-8" }));
    const a = document.createElement("a");
    a.href = url;
    a.download = `dealsieve-leads-${new Date().toISOString().slice(0, 10)}.csv`;
    document.body.appendChild(a);
    a.click();
    a.remove();
    URL.revokeObjectURL(url);
  },

  // Genuinely server-side: crawling, scoring and persistence.
  importFile: rejectServer,
  importSample: rejectServer,
  enrich: rejectServer,
  job: rejectServer,
  saveSettings: rejectServer,
  clear: rejectServer,
};
