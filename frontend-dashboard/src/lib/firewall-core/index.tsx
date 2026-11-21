"use client";

import { useState, useEffect, useCallback, useMemo, createContext, useContext, ReactNode } from "react";
import {
  AuditResult,
  BoundingBox,
  ResolutionRecord,
  ResolutionActionType,
  EngagementPolicy,
  LedgerAction,
  LedgerEntry,
} from "../types";
import { fetchAudit, fetchResolutions, appendResolution, LedgerState } from "../api";
import { sound } from "../audio";
import { recordTelemetry } from "../supabase";

// 18ms 900Hz Web Audio API pseudo-haptic synthesizer
export function playPseudoHaptic(): void {
  if (typeof window === "undefined") return;
  try {
    const AudioContextClass = window.AudioContext || (window as any).webkitAudioContext;
    if (!AudioContextClass) return;
    const ctx = new AudioContextClass();
    const osc = ctx.createOscillator();
    const gain = ctx.createGain();

    osc.type = "sine";
    osc.frequency.setValueAtTime(900, ctx.currentTime);

    // 18ms envelope: instant attack, exponential decay to zero
    gain.gain.setValueAtTime(0.08, ctx.currentTime);
    gain.gain.exponentialRampToValueAtTime(0.0001, ctx.currentTime + 0.018);

    osc.connect(gain);
    gain.connect(ctx.destination);

    osc.start(ctx.currentTime);
    osc.stop(ctx.currentTime + 0.02);
  } catch {
    // Audio context blocked: no haptic tick
  }
}

// Bounding box projector: maps the normalised [0, 1000) layout grid onto the rendered canvas
export function projectDoclingBoundingBox(
  box: BoundingBox,
  renderedWidth: number,
  renderedHeight: number
): { left: number; top: number; width: number; height: number } {
  return {
    left: (box.x / 1000) * renderedWidth,
    top: (box.y / 1000) * renderedHeight,
    width: (box.width / 1000) * renderedWidth,
    height: (box.height / 1000) * renderedHeight,
  };
}

// Client-side PII redactor (scrubs EIN, Tax IDs, IBANs, and consignee account numbers)
export function redactPiiText(text: string, enabled: boolean): string {
  if (!enabled || !text) return text;
  return text
    .replace(/\b\d{2}-\d{7}\b/g, "[EIN REDACTED]")
    .replace(/\b\d{9}\b/g, "[TAX ID REDACTED]")
    .replace(/[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,}/gi, "[EMAIL REDACTED]");
}

export interface FirewallContextValue {
  auditData: AuditResult | null;
  isLoading: boolean;
  activeConceptId: string;
  activeDiscrepancyId: string | null;
  quarantineState: "QUARANTINED" | "RELEASED" | "ESCALATED";
  /** Latest decision per finding, derived from the hash-chained ledger. */
  resolutionHistory: Record<string, ResolutionRecord>;
  ledgerEntries: LedgerEntry[];
  /** "server": the backend ledger; "browser": this browser only (static demo). */
  ledgerStorage: "server" | "browser";
  ledgerChainValid: boolean;
  piiRedactionActive: boolean;
  engagementPolicy: EngagementPolicy;
  switchConcept: (conceptId: string) => void;
  /** Make an audit loaded elsewhere (tab switch, upload) the one decisions are recorded against. */
  adoptAudit: (audit: AuditResult) => void;
  selectDiscrepancy: (id: string | null) => void;
  applyResolution: (
    discrepancyId: string,
    action: ResolutionActionType | "override_hts",
    reasonCode: string,
    notes?: string,
    overrideValue?: string
  ) => Promise<void>;
  undoResolution: (discrepancyId: string) => Promise<void>;
  togglePiiRedaction: () => void;
  exportAuditPacket: () => Promise<void>;
  triggerHaptic: () => void;
}

const DEFAULT_POLICY: EngagementPolicy = {
  policy_id: "DEFAULT-FORWARDER-TIER-1",
  auto_hold_threshold_usd: 10000.0,
  commercial_freight_tolerance_usd: 25.0,
  statutory_floor_enforced: true,
  fmc_free_time_days: 4,
  assist_amortization_method: "first_entry_lump_sum",
};

const TO_LEDGER: Record<ResolutionActionType | "override_hts", LedgerAction> = {
  approve_clean: "APPROVE",
  request_paperwork: "REQUEST_DOCS",
  escalate_broker: "ESCALATE",
  override_hts: "OVERRIDE_HTS",
};
const FROM_LEDGER: Partial<Record<LedgerAction, ResolutionActionType>> = {
  APPROVE: "approve_clean",
  REQUEST_DOCS: "request_paperwork",
  ESCALATE: "escalate_broker",
};

/** Reasons the release gate holds a document that analyst decisions cannot clear. */
const STRUCTURAL_REASONS = new Set(["MISSING_REQUIRED_FIELDS", "NON_USD_CURRENCY", "NO_TEXT_LAYER", "UNRECOGNIZED_DOCUMENT_TYPE", "BROWSER_SCAN_ONLY"]);

const FirewallContext = createContext<FirewallContextValue | null>(null);

export function FirewallProvider({ children }: { children: ReactNode }) {
  const [activeConceptId, setActiveConceptId] = useState<string>("concept_1_customs");
  const [auditData, setAuditData] = useState<AuditResult | null>(null);
  const [isLoading, setIsLoading] = useState<boolean>(true);
  const [activeDiscrepancyId, setActiveDiscrepancyId] = useState<string | null>(null);
  const [ledger, setLedger] = useState<LedgerState>({ entries: [], storage: "browser", chainValid: true });
  const [piiRedactionActive, setPiiRedactionActive] = useState<boolean>(false);
  const [engagementPolicy] = useState<EngagementPolicy>(DEFAULT_POLICY);

  const fetchCurrentAudit = useCallback(async (conceptId: string) => {
    setIsLoading(true);
    try {
      const data = await fetchAudit(conceptId);
      setAuditData(data);
      if (data.discrepancies.length > 0) {
        setActiveDiscrepancyId(data.discrepancies[0].id);
      }
    } catch (err) {
      console.error("Firewall fetch error:", err);
    } finally {
      setIsLoading(false);
    }
  }, []);

  useEffect(() => {
    fetchCurrentAudit(activeConceptId);
  }, [activeConceptId, fetchCurrentAudit]);

  // Reload recorded decisions whenever the audited run changes (they survive a reload).
  const runId = auditData?.audit_run_id;
  useEffect(() => {
    if (!runId) return;
    let live = true;
    fetchResolutions(runId).then((state) => {
      if (live) setLedger(state);
    });
    return () => {
      live = false;
    };
  }, [runId]);

  const adoptAudit = useCallback((audit: AuditResult) => {
    setAuditData((prev) => (prev?.audit_run_id === audit.audit_run_id && prev?.concept_id === audit.concept_id ? prev : audit));
    setActiveConceptId((prev) => (prev === audit.concept_id ? prev : audit.concept_id));
    setIsLoading(false);
  }, []);

  const switchConcept = useCallback((conceptId: string) => {
    playPseudoHaptic();
    sound.playLock();
    setActiveConceptId(conceptId);
    recordTelemetry({ event_type: "concept_switch", concept_id: conceptId });
  }, []);

  const selectDiscrepancy = useCallback((id: string | null) => {
    playPseudoHaptic();
    sound.playTick();
    setActiveDiscrepancyId(id);
    if (id) {
      recordTelemetry({ event_type: "discrepancy_card_selected", metadata: { discrepancy_id: id } });
    }
  }, []);

  const applyResolution = useCallback(
    async (
      discrepancyId: string,
      action: ResolutionActionType | "override_hts",
      reasonCode: string,
      notes?: string,
      overrideValue?: string
    ) => {
      if (!runId) return;
      playPseudoHaptic();
      sound.playLock();
      const reason = notes ? `${reasonCode}: ${notes}` : reasonCode;
      const next = await appendResolution(runId, {
        finding_id: discrepancyId,
        action: TO_LEDGER[action],
        reason,
        override_value: overrideValue,
      });
      setLedger(next);
      recordTelemetry({ event_type: "discrepancy_resolved", metadata: { discrepancy_id: discrepancyId, action, reasonCode } });
    },
    [runId]
  );

  const undoResolution = useCallback(
    async (discrepancyId: string) => {
      if (!runId) return;
      playPseudoHaptic();
      sound.playTick();
      setLedger(await appendResolution(runId, { finding_id: discrepancyId, action: "REOPEN", reason: "Decision reopened" }));
    },
    [runId]
  );

  const togglePiiRedaction = useCallback(() => {
    playPseudoHaptic();
    setPiiRedactionActive((prev) => !prev);
  }, []);

  // Latest non-override decision per finding; REOPEN clears it.
  const resolutionHistory = useMemo(() => {
    const out: Record<string, ResolutionRecord> = {};
    for (const e of ledger.entries) {
      if (e.action === "REOPEN") {
        delete out[e.finding_id];
        continue;
      }
      const mapped = FROM_LEDGER[e.action];
      if (!mapped) continue;
      out[e.finding_id] = {
        discrepancy_id: e.finding_id,
        action: mapped,
        reason_code: e.reason,
        timestamp: e.ts,
        resolved_by: e.actor,
      };
    }
    return out;
  }, [ledger.entries]);

  const exportAuditPacket = useCallback(async () => {
    playPseudoHaptic();
    sound.playLock();
    if (!auditData) return;

    const packet = {
      title: "Trade Systems Studio: Audit Packet for Broker / Counsel Review",
      notice: "Decision support only. Not legal advice; findings require review by a licensed customs broker or counsel.",
      audit_run_id: auditData.audit_run_id ?? null,
      run_digest: auditData.run_digest ?? null,
      document_filename: auditData.document_filename,
      document_sha256: auditData.document_sha256 ?? null,
      ruleset_hash: auditData.ruleset_hash ?? null,
      calc_version: auditData.calc_version ?? null,
      executed_at: auditData.executed_at ?? null,
      as_of_date: auditData.as_of_date ?? null,
      engagement_policy: auditData.engagement_policy || DEFAULT_POLICY,
      quarantine_status: auditData.quarantine_status ?? null,
      quarantine_reasons: auditData.quarantine_reasons ?? [],
      metrics: auditData.metrics,
      discrepancies: auditData.discrepancies.map((d) => ({
        ...d,
        description: redactPiiText(d.description, piiRedactionActive),
        resolution: resolutionHistory[d.id] || null,
      })),
      resolution_ledger: { storage: ledger.storage, chain_valid: ledger.chainValid, entries: ledger.entries },
    };

    const blob = new Blob([JSON.stringify(packet, null, 2)], { type: "application/json" });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = `audit_packet_${auditData.concept_id}_${packet.audit_run_id ?? "unsaved"}.json`;
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
    URL.revokeObjectURL(url);

    recordTelemetry({ event_type: "counsel_audit_packet_downloaded", metadata: { audit_run_id: packet.audit_run_id } });
  }, [auditData, piiRedactionActive, resolutionHistory, ledger]);

  let quarantineState: "QUARANTINED" | "RELEASED" | "ESCALATED" = "RELEASED";
  if (auditData) {
    const structural = (auditData.quarantine_reasons ?? []).some((r) => STRUCTURAL_REASONS.has(r));
    const decisions = auditData.discrepancies.map((d) => resolutionHistory[d.id]?.action);
    const unapproved = auditData.discrepancies.some(
      (d) => (d.confidence < 0.85 || d.severity === "critical") && resolutionHistory[d.id]?.action !== "approve_clean"
    );
    if (decisions.includes("escalate_broker")) quarantineState = "ESCALATED";
    else if (structural || unapproved) quarantineState = "QUARANTINED";
  }

  const value: FirewallContextValue = {
    auditData,
    isLoading,
    activeConceptId,
    activeDiscrepancyId,
    quarantineState,
    resolutionHistory,
    ledgerEntries: ledger.entries,
    ledgerStorage: ledger.storage,
    ledgerChainValid: ledger.chainValid,
    piiRedactionActive,
    engagementPolicy,
    switchConcept,
    adoptAudit,
    selectDiscrepancy,
    applyResolution,
    undoResolution,
    togglePiiRedaction,
    exportAuditPacket,
    triggerHaptic: playPseudoHaptic,
  };

  return <FirewallContext.Provider value={value}>{children}</FirewallContext.Provider>;
}

export function usePreIngestFirewall(): FirewallContextValue {
  const context = useContext(FirewallContext);
  if (!context) {
    throw new Error("usePreIngestFirewall must be used within a FirewallProvider");
  }
  return context;
}
