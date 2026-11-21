import {
  AuditResult,
  KillShotMetrics,
  CorporateGraphResponse,
  HTSClassificationResult,
  AssistItem,
  EntryValuationAudit,
  PriorDisclosurePackage,
  LeadCapturePayload,
  CargoWiseDiff,
  LedgerAction,
  LedgerEntry,
} from "./types";
import {
  MOCK_AUDIT_DATA,
  AGGREGATE_METRICS,
  MOCK_SANCTIONS_GRAPHS,
  MOCK_HTS_PRESETS,
  MOCK_ASSIST_ITEMS,
  MOCK_VALUATION_AUDIT,
  MOCK_PRIOR_DISCLOSURE,
  MOCK_CARGOWISE_DIFFS,
} from "@/data/mockData";
import { calculateClientLandedCost } from "./money";
import { reportDataSource } from "./dataSource";

// On public static hosts (GitHub Pages) there is no backend, and loopback fetches to
// localhost:8000 are blocked by Private Network Access, so no API base is used there.
const isBrowser = typeof window !== "undefined";
const isPublicHost =
  isBrowser && window.location.hostname !== "localhost" && window.location.hostname !== "127.0.0.1";
const isOfflineForced = process.env.NEXT_PUBLIC_OFFLINE_MODE === "true";
const API_BASE = isOfflineForced
  ? ""
  : process.env.NEXT_PUBLIC_API_URL || (isPublicHost ? "" : "http://localhost:8000");

export function isOfflineMode(): boolean {
  return !API_BASE;
}

export class ApiError extends Error {
  constructor(public status: number, message: string) {
    super(message);
  }
}

async function getJson<T>(path: string, init?: RequestInit): Promise<T> {
  const res = await fetch(`${API_BASE}${path}`, { cache: "no-store", ...init });
  if (!res.ok) {
    let detail = `HTTP ${res.status}`;
    try {
      const body = await res.json();
      if (body?.detail) detail = typeof body.detail === "string" ? body.detail : JSON.stringify(body.detail);
    } catch {
      /* non-JSON error body */
    }
    throw new ApiError(res.status, detail);
  }
  return (await res.json()) as T;
}

function describe(err: unknown): string {
  if (err instanceof ApiError) return `Backend error ${err.status}: ${err.message}`;
  return "Backend unreachable";
}

/**
 * Live result when a backend is configured; otherwise the build-time snapshot.
 * If a configured backend fails, the snapshot is shown and the failure is reported
 * (the UI shows a banner). Unknown keys never fall back to a different record.
 */
async function liveOrSnapshot<T>(path: string, snapshot: T | undefined, init?: RequestInit): Promise<T> {
  if (!API_BASE) {
    if (snapshot === undefined) throw new ApiError(404, "Not available in the offline demo");
    reportDataSource("snapshot");
    return snapshot;
  }
  try {
    const data = await getJson<T>(path, init);
    reportDataSource("live");
    return data;
  } catch (err) {
    if (snapshot === undefined || (err instanceof ApiError && err.status < 500 && err.status !== 429)) {
      reportDataSource("live", describe(err));
      throw err;
    }
    reportDataSource("snapshot", describe(err));
    return snapshot;
  }
}

/** Backend document URLs are relative to the API origin, not the page origin. */
function withAbsoluteDocumentUrl(audit: AuditResult): AuditResult {
  if (API_BASE && audit.document_url?.startsWith("/api/")) {
    return { ...audit, document_url: `${API_BASE}${audit.document_url}` };
  }
  return audit;
}

export async function fetchAudit(conceptId: string): Promise<AuditResult> {
  const audit = await liveOrSnapshot(`/api/v1/audit/${encodeURIComponent(conceptId)}`, MOCK_AUDIT_DATA[conceptId]);
  return withAbsoluteDocumentUrl(audit);
}

export function fetchAggregateMetrics(): Promise<KillShotMetrics> {
  return liveOrSnapshot("/api/v1/metrics", AGGREGATE_METRICS);
}

export function fetchCargoWiseDiff(conceptId: string): Promise<CargoWiseDiff> {
  return liveOrSnapshot(`/api/v1/cargowise/export/${encodeURIComponent(conceptId)}`, MOCK_CARGOWISE_DIFFS[conceptId]);
}

/** An entity with no ownership record: shown as a compliance hold, never as another entity's graph. */
function unknownEntityGraph(entityId: string): CorporateGraphResponse {
  return {
    target_id: entityId,
    nodes: [{ id: entityId, label: entityId, country: "UNKNOWN", is_blocked: false, risk_level: "COMPLIANCE_HOLD", programs: [] }],
    edges: [],
    evaluation: {
      target_entity_id: entityId,
      target_entity_name: entityId,
      total_blocked_ownership_pct: 0,
      is_blocked_by_50_percent_rule: false,
      direct_sdn_status: false,
      statutory_citation: "31 CFR § 501 (OFAC 50 Percent Rule)",
      blocking_entities: [],
      compliance_action: "REQUIRES_MANUAL_REVIEW",
    },
  };
}

export async function fetchSanctionsGraph(entityId: string): Promise<CorporateGraphResponse> {
  const snap = MOCK_SANCTIONS_GRAPHS[entityId] ?? (API_BASE ? undefined : unknownEntityGraph(entityId));
  return liveOrSnapshot(`/api/v1/sanctions/graph/${encodeURIComponent(entityId)}`, snap);
}

// -------------------------------------------------------------
// Resolutions ledger (hash-chained, server-side)
// -------------------------------------------------------------
const LOCAL_LEDGER_KEY = "tss.resolutions.v1";

function readLocalLedger(runId: string): LedgerEntry[] {
  try {
    const all = JSON.parse(window.localStorage.getItem(LOCAL_LEDGER_KEY) || "{}");
    return Array.isArray(all[runId]) ? all[runId] : [];
  } catch {
    return [];
  }
}

function writeLocalLedger(runId: string, rows: LedgerEntry[]): void {
  try {
    const all = JSON.parse(window.localStorage.getItem(LOCAL_LEDGER_KEY) || "{}");
    all[runId] = rows;
    window.localStorage.setItem(LOCAL_LEDGER_KEY, JSON.stringify(all));
  } catch {
    /* storage unavailable (private mode): decisions stay in memory only */
  }
}

async function sha256Hex(text: string): Promise<string> {
  const buf = await crypto.subtle.digest("SHA-256", new TextEncoder().encode(text));
  return Array.from(new Uint8Array(buf))
    .map((b) => b.toString(16).padStart(2, "0"))
    .join("");
}

export interface LedgerState {
  entries: LedgerEntry[];
  /** "server": persisted in the backend ledger; "browser": this browser only (static demo). */
  storage: "server" | "browser";
  chainValid: boolean;
}

export async function fetchResolutions(runId: string): Promise<LedgerState> {
  if (API_BASE) {
    try {
      const data = await getJson<{ chain_valid: boolean; resolutions: LedgerEntry[] }>(
        `/api/v1/audit/${encodeURIComponent(runId)}/resolutions`
      );
      return { entries: data.resolutions, storage: "server", chainValid: data.chain_valid };
    } catch {
      /* fall through to the browser copy */
    }
  }
  return { entries: readLocalLedger(runId), storage: "browser", chainValid: true };
}

export async function appendResolution(
  runId: string,
  entry: { finding_id: string; action: LedgerAction; reason: string; actor?: string; override_value?: string }
): Promise<LedgerState> {
  if (API_BASE) {
    await getJson<LedgerEntry>(`/api/v1/audit/${encodeURIComponent(runId)}/resolutions`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ actor: "analyst", ...entry }),
    });
    return fetchResolutions(runId);
  }
  // Static demo: the same hash chain, kept in this browser only.
  const rows = readLocalLedger(runId);
  const prev = rows.length ? rows[rows.length - 1].hash : "0".repeat(64);
  const row = {
    run_id: runId,
    finding_id: entry.finding_id,
    action: entry.action,
    reason: entry.reason,
    actor: entry.actor ?? "analyst",
    override_value: entry.override_value ?? null,
    ts: new Date().toISOString(),
  };
  const hash = await sha256Hex(`${prev}|${JSON.stringify(row, Object.keys(row).sort())}`);
  const next = [...rows, { ...row, seq: rows.length + 1, prev_hash: prev, hash }];
  writeLocalLedger(runId, next);
  return { entries: next, storage: "browser", chainValid: true };
}

// -------------------------------------------------------------
// Pillar 3: HTS Classification Copilot API
// -------------------------------------------------------------
function withClientLandedCost(
  base: HTSClassificationResult,
  enteredValue: number,
  isOceanFreight: boolean,
  freight?: number | string
): HTSClassificationResult {
  return {
    ...base,
    landed_cost: calculateClientLandedCost({
      enteredValue,
      dutyRateAdValorem: base.landed_cost.duty_rate_ad_valorem,
      isOceanFreight,
      freightAndInsurance: freight ?? base.landed_cost.freight_and_insurance ?? "1500.00",
      section301Rate: base.landed_cost.section_301_rate || "0.00",
    }),
  };
}

export async function fetchHtsPreset(
  presetId: string,
  enteredValue: number = 45000,
  isOceanFreight: boolean = true
): Promise<HTSClassificationResult> {
  const base = MOCK_HTS_PRESETS[presetId];
  if (!API_BASE) {
    reportDataSource("snapshot");
    if (!base) throw new ApiError(404, `Unknown preset ${presetId}`);
    return withClientLandedCost(base, enteredValue, isOceanFreight);
  }
  try {
    const data = await getJson<HTSClassificationResult>(
      `/api/v1/hts/preset/${encodeURIComponent(presetId)}?entered_value=${enteredValue}`
    );
    reportDataSource("live");
    return data;
  } catch (err) {
    reportDataSource("snapshot", describe(err));
    if (!base) throw err;
    return withClientLandedCost(base, enteredValue, isOceanFreight);
  }
}

const NON_APPARATUS_EXCLUSIONS_FE = [
  /\b(?:t-?shirts?|hoodies?|clothing|apparel|hats?|caps?|socks?|jackets?)\b/i,
  /\b(?:shaving\s+cream|cosmetics?|lotions?|soaps?|shampoos?)\b/i,
  /\b(?:paintings?|artwork|posters?|canvas(?:es)?|drawings?)\b/i,
  /\b(?:oils?|greases?|lubricants?|fuels?|additives?)\b/i,
  /\b(?:keycaps?|keyboard\s+keys?|novelty|stickers?|decals?|patch(?:es)?)\b/i,
  /\b(?:foods?|supplements?|vitamins?|powders?|capsules?|pills?)\b/i,
  /\b(?:books?|manuals?|magazines?|guides?|catalogs?)\b/i,
];

function matchOfflinePreset(text: string): HTSClassificationResult | null {
  const t = text.toLowerCase();
  if (NON_APPARATUS_EXCLUSIONS_FE.some((rx) => rx.test(t))) return null;
  if (/\b(?:motor|drone|uav|brushless|esc|speed\s+controller)\b/i.test(t)) return MOCK_HTS_PRESETS["drone_motor"];
  if (/\b(?:accelerator|tensor|pcie|gpu|npu|neural|processor)\b/i.test(t)) return MOCK_HTS_PRESETS["server_accelerator"];
  if (/\b(?:battery|lifepo4|accumulator|lithium|energy\s+storage|pack)\b/i.test(t)) return MOCK_HTS_PRESETS["ev_battery_pack"];
  if (/\b(?:fitness|smartband|smartwatch|wearable|ppg|biometric)\b/i.test(t)) return MOCK_HTS_PRESETS["smart_apparel_watch"];
  return null;
}

function unclassified(payload: { product_title: string; product_description: string; entered_value: number; is_ocean_freight?: boolean; freight_and_insurance?: number }): HTSClassificationResult {
  return {
    item_id: "hts-unclassified",
    product_title: payload.product_title,
    input_description: payload.product_description,
    country_of_origin: "UNKNOWN",
    classified_hts_code: "REQUIRES_BROKER_REVIEW",
    confidence: 0.0,
    requires_human_review: true,
    gri_path: [],
    chapter_notes_cited: [
      "Unclassified merchandise: the description does not match a pre-computed GRI pattern.",
      "Classification must be reviewed by a licensed customs broker (19 CFR Part 111) before entry.",
    ],
    landed_cost: calculateClientLandedCost({
      enteredValue: payload.entered_value,
      dutyRateAdValorem: "0.00",
      isOceanFreight: payload.is_ocean_freight ?? true,
      freightAndInsurance: payload.freight_and_insurance ?? 0,
    }),
  };
}

export async function classifyHtsProduct(payload: {
  product_title: string;
  product_description: string;
  commercial_attributes?: string;
  entered_value: number;
  is_ocean_freight?: boolean;
  freight_and_insurance?: number;
}): Promise<HTSClassificationResult> {
  const offline = () => {
    const matched = matchOfflinePreset(`${payload.product_title} ${payload.product_description}`);
    return matched
      ? withClientLandedCost(matched, payload.entered_value, payload.is_ocean_freight ?? true, payload.freight_and_insurance)
      : unclassified(payload);
  };
  if (!API_BASE) {
    reportDataSource("snapshot");
    return offline();
  }
  try {
    const data = await getJson<HTSClassificationResult>("/api/v1/hts/classify", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload),
    });
    reportDataSource("live");
    return data;
  } catch (err) {
    reportDataSource("snapshot", describe(err));
    return offline();
  }
}

// -------------------------------------------------------------
// Pillar 4: CBP Assist & Valuation Register API
// -------------------------------------------------------------
const VALUATION_REQUEST = {
  entry_number: "CBP-7501-84920184",
  importer_of_record: "Pacific Tech Imports LLC (EIN 94-8291048)",
  declared_transaction_value: "450000.00",
  duty_rate_ad_valorem: "0.054",
  current_entry_units: 15000,
  invoice_incoterm: "CIF Los Angeles",
  international_freight_in_invoice: "24500.00",
  marine_insurance_in_invoice: "3200.00",
  months_elapsed: 9,
};

export function fetchValuationLedger(): Promise<AssistItem[]> {
  return liveOrSnapshot("/api/v1/valuation/ledger", MOCK_ASSIST_ITEMS);
}

export function fetchValuationAudit(): Promise<EntryValuationAudit> {
  return liveOrSnapshot("/api/v1/valuation/audit-entry", MOCK_VALUATION_AUDIT, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(VALUATION_REQUEST),
  });
}

export function generatePriorDisclosurePackage(): Promise<PriorDisclosurePackage> {
  return liveOrSnapshot("/api/v1/valuation/prior-disclosure", MOCK_PRIOR_DISCLOSURE, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(VALUATION_REQUEST),
  });
}

// -------------------------------------------------------------
// Leads
// -------------------------------------------------------------
const LEAD_ENDPOINT = process.env.NEXT_PUBLIC_LEAD_ENDPOINT || "";

export async function submitLeadApi(
  payload: LeadCapturePayload
): Promise<{ success: boolean; id?: string; error?: string }> {
  const target = LEAD_ENDPOINT || (API_BASE ? `${API_BASE}/api/v1/leads` : "");
  if (!target) return { success: false, error: "STATIC_HOST_NO_BACKEND" };
  try {
    const res = await fetch(target, {
      method: "POST",
      headers: { "Content-Type": "application/json", Accept: "application/json" },
      body: JSON.stringify(payload),
    });
    if (!res.ok) return { success: false, error: `Lead endpoint error ${res.status}` };
    const data = await res.json().catch(() => ({}));
    return { success: true, id: data.lead_id || data.id };
  } catch (err) {
    return { success: false, error: err instanceof Error ? err.message : "NETWORK_ERROR" };
  }
}

// -------------------------------------------------------------
// Document upload
// -------------------------------------------------------------
/**
 * Audit an uploaded PDF. With a backend configured, its answer is final: a 4xx/5xx is
 * surfaced to the user (e.g. "Unreadable PDF"), never replaced by a local guess. Only
 * when no backend is configured, or it cannot be reached at all, does the in-browser
 * scanner run, and its result is marked source="client".
 */
export async function uploadAndAuditDocument(file: File): Promise<AuditResult> {
  if (API_BASE) {
    const formData = new FormData();
    formData.append("file", file);
    let res: Response | null = null;
    try {
      res = await fetch(`${API_BASE}/api/v1/audit/upload`, { method: "POST", body: formData });
    } catch {
      reportDataSource("client", "Backend unreachable: scanned in the browser instead");
    }
    if (res) {
      if (!res.ok) {
        const body = await res.json().catch(() => ({}));
        const msg = typeof body?.detail === "string" ? body.detail : `HTTP ${res.status}`;
        reportDataSource("live", `Upload rejected: ${msg}`);
        throw new ApiError(res.status, msg);
      }
      reportDataSource("live");
      const audit = (await res.json()) as AuditResult;
      // The backend does not host uploads; show the user's own file from memory.
      return { ...audit, document_url: audit.document_url || URL.createObjectURL(file) };
    }
  } else {
    reportDataSource("client");
  }
  const { auditUploadedPdf } = await import("./clientAuditor");
  return await auditUploadedPdf(file);
}
