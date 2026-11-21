import { createClient } from "@supabase/supabase-js";
import { LeadCapturePayload, TelemetryPayload } from "./types";

const supabaseUrl = process.env.NEXT_PUBLIC_SUPABASE_URL || "";
const supabaseAnonKey = process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY || "";

export const isSupabaseConfigured = Boolean(supabaseUrl && supabaseAnonKey);

export const supabase = isSupabaseConfigured
  ? createClient(supabaseUrl, supabaseAnonKey)
  : null;

/**
 * Persists lead capture to Supabase if configured; returns error status if unavailable.
 */
export async function submitLeadCapture(lead: LeadCapturePayload): Promise<{ success: boolean; id?: string; error?: string }> {
  try {
    if (supabase) {
      const { data, error } = await supabase
        .from("audit_leads")
        .insert([
          {
            email: lead.email,
            company_name: lead.company_name,
            phone: lead.phone || null,
            monthly_import_volume: lead.monthly_import_volume || null,
            source: lead.source || "conversion_modal",
            created_at: new Date().toISOString(),
          },
        ])
        .select();

      if (error) {
        console.warn("Supabase lead insertion warning:", error.message);
        return { success: false, error: error.message };
      } else if (data && data[0]) {
        return { success: true, id: data[0].id };
      }
    }

    return { success: false, error: "UNAVAILABLE" };
  } catch (err: any) {
    console.warn("Supabase lead submission error:", err);
    return { success: false, error: err?.message || "UNAVAILABLE" };
  }
}

const TELEMETRY_CONSENT_KEY = "tradetech_telemetry_consent";
const PII_KEYS = new Set(["name", "email", "phone", "company", "company_name", "full_name"]);

export function isTelemetryConsentGranted(): boolean {
  if (typeof window === "undefined") return false;
  try {
    return window.localStorage.getItem(TELEMETRY_CONSENT_KEY) === "granted";
  } catch {
    return false;
  }
}

export function setTelemetryConsent(granted: boolean): void {
  if (typeof window === "undefined") return;
  try {
    if (granted) {
      window.localStorage.setItem(TELEMETRY_CONSENT_KEY, "granted");
    } else {
      window.localStorage.removeItem(TELEMETRY_CONSENT_KEY);
      window.localStorage.removeItem("telemetry_cache");
    }
  } catch {
    // Storage unavailable
  }
}

function sanitizeTelemetryMetadata(metadata?: Record<string, any>): Record<string, any> {
  if (!metadata || typeof metadata !== "object") return {};
  const clean: Record<string, any> = {};
  for (const [k, v] of Object.entries(metadata)) {
    if (!PII_KEYS.has(k.toLowerCase())) {
      clean[k] = v;
    }
  }
  return clean;
}

/**
 * Tracks strictly zero-PII telemetry events ONLY when explicit user consent is granted.
 */
export async function recordTelemetry(event: TelemetryPayload): Promise<void> {
  if (!isTelemetryConsentGranted()) {
    return;
  }
  const safeMetadata = sanitizeTelemetryMetadata(event.metadata);
  try {
    if (supabase) {
      await supabase.from("telemetry_events").insert([
        {
          event_type: event.event_type,
          concept_id: event.concept_id || null,
          discrepancy_id: event.discrepancy_id || null,
          metadata: safeMetadata,
          created_at: new Date().toISOString(),
        },
      ]);
      return;
    }

    // Local fallback (strictly zero-PII, consent-gated)
    if (typeof window !== "undefined") {
      const stored = JSON.parse(localStorage.getItem("telemetry_cache") || "[]");
      stored.push({
        event_type: event.event_type,
        concept_id: event.concept_id || null,
        discrepancy_id: event.discrepancy_id || null,
        metadata: safeMetadata,
        timestamp: new Date().toISOString(),
      });
      if (stored.length > 50) stored.shift();
      localStorage.setItem("telemetry_cache", JSON.stringify(stored));
    }
  } catch {
    // Telemetry is best-effort and never blocks the UI
  }
}
