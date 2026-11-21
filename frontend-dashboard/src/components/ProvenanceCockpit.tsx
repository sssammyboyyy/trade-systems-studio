"use client";

import React, { useState } from "react";
import { AuditResult, Discrepancy, LedgerEntry } from "@/lib/types";
import { formatUsd } from "@/lib/money";
import { usePreIngestFirewall } from "@/lib/firewall-core";
import {
  AlertTriangle,
  CheckCircle2,
  ChevronDown,
  Lock,
  Scale,
  ShieldCheck,
  Copy,
  Check,
  Terminal,
  Download,
} from "lucide-react";

const CONFIDENCE_GATE = 0.85;

const short = (h?: string | null, head = 8, tail = 6) => (h ? `${h.slice(0, head)}…${h.slice(-tail)}` : "n/a");

/**
 * Explains a finding using only the values the engine returned in its metadata.
 * Nothing here is a prose literal about a particular fixture.
 */
export function getProvenanceTrace(d: Discrepancy): { steps: string[]; formula: string | null } {
  const m = d.metadata ?? {};
  const bb = d.bounding_box;
  const anchored = m.layout_verified
    ? `Anchored to text "${m.layout_anchor}" on page ${bb.page_number} of this document`
    : "Not anchored to document text (template region): verify on the page";
  const steps = [anchored, `Rule: ${d.statutory_code}`];
  let formula: string | null = null;

  if (m.penalty_basis === "19_USC_1592" && m.duty_loss) {
    const tiers = m.statutory_max_by_culpability ?? {};
    steps.push(`Loss of duty ${formatUsd(m.duty_loss)} on a base of ${formatUsd(m.dutiable_base)}`);
    steps.push(
      `Statutory maximums: negligence ${tiers.negligence ? formatUsd(tiers.negligence) : "n/a"}, gross negligence ${
        tiers.gross_negligence ? formatUsd(tiers.gross_negligence) : "n/a"
      }, fraud ${tiers.fraud ? formatUsd(tiers.fraud) : "domestic value (not stated)"}`
    );
    steps.push(`Shown: ${String(m.culpability_assumed).replace("_", " ")} (the default; culpability is for counsel)`);
    formula = `loss = ${m.dutiable_base} × (lawful − declared rate) = ${m.duty_loss}`;
  } else if (m.variance !== undefined && m.calculated_total !== undefined) {
    steps.push(`Recomputed ${m.calculated_total} vs stated ${m.stated_total}`);
    formula = `stated ${m.stated_total} − qty × unit price ${m.calculated_total} = ${m.variance}`;
  } else if (m.non_dutiable_charges !== undefined) {
    steps.push(`Non-dutiable CIF charges itemised: ${formatUsd(m.non_dutiable_charges)}`);
    formula = m.estimated_excess_duty
      ? `${m.non_dutiable_charges} × effective rate ${m.effective_duty_rate} = ${m.estimated_excess_duty} excess duty`
      : "Excess duty not computed: at least one line's duty rate is unknown";
  } else if (m.billed_fsc !== undefined) {
    formula = `billed ${m.billed_fsc} − contracted ${m.lawful_fsc} = ${m.variance}`;
  } else if (m.days_held !== undefined) {
    formula = `day ${m.days_held} of ${m.free_days_allowed} ${m.free_time_basis ?? ""} free days → ${m.illegal_detention} not owed`;
  } else if (m.cash_recovery_ready !== undefined) {
    steps.push(`Basis ${m.basis === "j1" ? "(j)(1) direct identification" : "(j)(2) substitution"}; ${m.timeliness}`);
    formula = `${m.eligible_quantity} units × ${m.duty_per_unit} × ${m.statutory_percent} = ${m.cash_recovery_ready}`;
  } else if (m.blocked_ownership_pct !== undefined) {
    formula = `aggregate blocked ownership ${m.blocked_ownership_pct} ≥ 50% → blocked`;
  }
  return { steps, formula };
}

/** Document-level lineage strip, read entirely from the audit payload. */
export const ProvenanceMetadataBar: React.FC<{ audit: AuditResult | null }> = ({ audit }) => {
  const [copied, setCopied] = useState(false);
  if (!audit) return null;

  const sha = audit.document_sha256 ?? null;
  const copySha = () => {
    if (!sha) return;
    navigator.clipboard.writeText(sha);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };
  const status = audit.quarantine_status ?? "QUARANTINED";

  return (
    <div className="mb-3 flex flex-wrap items-center justify-between gap-x-4 gap-y-2 rounded-lg border border-terminal-subtle bg-canvas-dark px-3 py-2 type-caption-mono text-ink-muted">
      <div className="flex min-w-0 flex-wrap items-center gap-x-4 gap-y-1">
        <span className="flex items-center gap-1.5 font-medium uppercase text-ink-emerald">
          <Lock className="h-3 w-3" aria-hidden /> Provenance
        </span>
        <span className="flex min-w-0 items-center gap-1.5">
          <span className="uppercase">Document</span>
          <span className="truncate text-ink-secondary">{audit.document_filename}</span>
        </span>
        <button
          onClick={copySha}
          disabled={!sha}
          title={sha ? `SHA-256 ${sha} (click to copy; compare with shasum -a 256)` : "No document hash"}
          className="flex items-center gap-1 transition-colors hover:text-ink-primary disabled:cursor-default"
        >
          <span className="uppercase">SHA-256</span>
          <span className="text-ink-cobalt">{short(sha)}</span>
          {sha && (copied ? <Check className="h-2.5 w-2.5 text-ink-emerald" /> : <Copy className="h-2.5 w-2.5" />)}
        </button>
        <span className="flex items-center gap-1.5" title={audit.run_digest ?? undefined}>
          <span className="uppercase">Run</span>
          <span className="text-ink-secondary">{audit.audit_run_id ?? "n/a"}</span>
        </span>
        <span className="flex items-center gap-1.5" title={audit.ruleset_hash ?? undefined}>
          <span className="uppercase">Rules</span>
          <span className="text-ink-secondary">
            {audit.calc_version ?? "n/a"} · {short(audit.ruleset_hash, 6, 4)}
          </span>
        </span>
        {audit.as_of_date && (
          <span className="flex items-center gap-1.5">
            <span className="uppercase">As of</span>
            <span className="text-ink-secondary tabular-nums">{audit.as_of_date}</span>
          </span>
        )}
      </div>
      <span
        className={`rounded border px-1.5 py-0.5 font-medium uppercase ${
          status === "RELEASED"
            ? "border-status-emerald/40 text-ink-emerald"
            : "border-status-amber/40 text-ink-amber"
        }`}
        title={(audit.quarantine_reasons ?? []).join(", ") || undefined}
      >
        {status === "RELEASED" ? "Released" : `Held: ${(audit.quarantine_reasons ?? ["review"]).join(", ").toLowerCase().replace(/_/g, " ")}`}
      </span>
    </div>
  );
};

const HIDDEN_KEYS = new Set(["layout_verified", "layout_anchor", "bbox_source", "extraction_source", "statutory_max_by_culpability", "rate_sources", "blocking_entities"]);

export const DecisionProvenanceCard: React.FC<{ discrepancy: Discrepancy }> = ({ discrepancy }) => {
  const isGated = discrepancy.confidence < CONFIDENCE_GATE;
  const bbox = discrepancy.bounding_box;
  const trace = getProvenanceTrace(discrepancy);
  const operands = Object.entries(discrepancy.metadata ?? {}).filter(
    ([k, v]) => !HIDDEN_KEYS.has(k) && v !== null && v !== undefined && typeof v !== "object"
  );

  return (
    <div className="space-y-2 p-3 text-[11px]">
      <div className="grid grid-cols-[74px_1fr] gap-2">
        <span className="uppercase tracking-wider text-ink-muted">Location</span>
        <span className="text-ink-secondary">
          Page {bbox.page_number} · x{Math.round(bbox.x)} y{Math.round(bbox.y)} · {discrepancy.metadata?.layout_verified ? "anchored to text" : "approximate region"}
        </span>
      </div>
      <div className="grid grid-cols-[74px_1fr] gap-2">
        <span className="uppercase tracking-wider text-ink-muted">Rule</span>
        <span className="statutory-cite text-[13px] text-ink-cobalt">{discrepancy.statutory_code}</span>
      </div>
      <div className="grid grid-cols-[74px_1fr] gap-2">
        <span className="uppercase tracking-wider text-ink-muted">Amount</span>
        <span className="type-mono-data font-medium tabular-nums text-ink-crimson">{formatUsd(discrepancy.exposure_amount)}</span>
      </div>
      <div className="grid grid-cols-[74px_1fr] gap-2">
        <span className="uppercase tracking-wider text-ink-muted">Confidence</span>
        <span className={`type-mono-data tabular-nums ${isGated ? "font-medium text-ink-amber" : "text-ink-emerald"}`}>
          {(discrepancy.confidence * 100).toFixed(0)}% {isGated ? "(below the 85% review gate)" : ""}
        </span>
      </div>

      <div className="mt-2 space-y-1.5 border-t border-terminal-subtle pt-2">
        <div className="flex items-center gap-1.5 text-[10px] font-bold uppercase tracking-wider text-ink-muted">
          <Scale className="h-3 w-3 text-cobalt-400" aria-hidden /> How this was derived
        </div>
        <ol className="space-y-1 border-l-2 border-cobalt-600/60 pl-2 font-mono text-[10px]">
          {trace.steps.map((step, idx) => (
            <li key={idx} className="flex items-start gap-1.5 text-ink-secondary">
              <span className="shrink-0 font-bold text-cobalt-400">{idx + 1}.</span>
              <span>{step}</span>
            </li>
          ))}
        </ol>
      </div>

      {trace.formula && (
        <div className="space-y-1 rounded-md border border-cobalt-900/40 bg-canvas-dark p-2 font-mono text-[10px]">
          <div className="flex items-center gap-1 text-[9px] font-semibold uppercase tracking-wider text-ink-muted">
            <Terminal className="h-3 w-3 text-ink-emerald" aria-hidden /> Decimal arithmetic (from the engine output)
          </div>
          <div className="break-all font-bold text-ink-emerald">{trace.formula}</div>
        </div>
      )}

      {operands.length > 0 && (
        <details className="border-t border-terminal-subtle pt-1.5">
          <summary className="cursor-pointer uppercase tracking-wider text-ink-muted">Engine operands ({operands.length})</summary>
          <div className="mt-1 space-y-0.5">
            {operands.map(([key, value]) => (
              <div key={key} className="flex gap-1.5">
                <span className="text-ink-muted">{key}:</span>
                <span className="break-all text-ink-secondary">{String(value)}</span>
              </div>
            ))}
          </div>
        </details>
      )}
    </div>
  );
};

export const ContestableOverridePanel: React.FC<{
  isOpen: boolean;
  onClose: () => void;
  onCommit: (code: string, justification: string, memo: string) => void;
}> = ({ isOpen, onClose, onCommit }) => {
  const [correctedCode, setCorrectedCode] = useState<string>("");
  const [justification, setJustification] = useState<string>("CBP binding ruling");
  const [memo, setMemo] = useState<string>("");
  if (!isOpen) return null;

  const valid = /^\d{4}\.\d{2}\.\d{4}$/.test(correctedCode.trim());
  const inputCls =
    "w-full rounded-md border border-terminal-subtle bg-canvas-dark px-2.5 py-1.5 font-mono text-[11px] text-ink-primary focus:border-cobalt-600 focus:outline-none";

  return (
    <div className="space-y-2 border-t border-terminal-subtle bg-canvas-dark/50 px-3 pb-3 pt-3">
      <label className="block text-[10px] font-bold uppercase tracking-wider text-ink-muted" htmlFor="override-hts">
        Corrected HTS (10 digits, e.g. 8542.31.0000)
      </label>
      <input id="override-hts" value={correctedCode} onChange={(e) => setCorrectedCode(e.target.value)} placeholder="8542.31.0000" className={inputCls} />
      <label className="block text-[10px] font-bold uppercase tracking-wider text-ink-muted" htmlFor="override-why">
        Justification
      </label>
      <select id="override-why" value={justification} onChange={(e) => setJustification(e.target.value)} className={inputCls}>
        <option>CBP binding ruling</option>
        <option>GRI 3(b) essential character</option>
        <option>Section XVI legal note</option>
        <option>Chapter note / explanatory note</option>
      </select>
      <label className="block text-[10px] font-bold uppercase tracking-wider text-ink-muted" htmlFor="override-memo">
        Reviewer memo
      </label>
      <textarea id="override-memo" value={memo} onChange={(e) => setMemo(e.target.value)} rows={2} placeholder="Why the classification differs" className={`${inputCls} resize-none`} />
      <div className="flex items-center justify-end gap-2 pt-1">
        <button onClick={onClose} className="rounded-md border border-terminal-subtle px-2.5 py-1.5 text-[10px] font-bold uppercase tracking-wider text-ink-muted transition-colors hover:text-ink-primary">
          Cancel
        </button>
        <button
          onClick={() => {
            onCommit(correctedCode.trim(), justification, memo);
            setCorrectedCode("");
            setMemo("");
          }}
          disabled={!valid}
          className="rounded-md bg-cobalt-600 px-3 py-1.5 text-[10px] font-bold uppercase tracking-wider text-canvas-stone transition-colors hover:bg-cobalt-500 disabled:cursor-not-allowed disabled:opacity-40"
        >
          Record override
        </button>
      </div>
    </div>
  );
};

const ACTION_STYLE: Record<string, string> = {
  APPROVE: "border-status-emerald/50 text-ink-emerald",
  OVERRIDE_HTS: "border-status-amber/50 text-ink-amber",
  REQUEST_DOCS: "border-status-amber/50 text-ink-amber",
  ESCALATE: "border-status-crimson/50 text-ink-crimson",
  REOPEN: "border-terminal-border text-ink-muted",
};

/** Hash-chained decision log for one finding (server ledger, or this browser in the static demo). */
export const DecisionLedgerLog: React.FC<{
  entries: LedgerEntry[];
  storage: "server" | "browser";
  chainValid: boolean;
  isOpen: boolean;
  onToggle: () => void;
}> = ({ entries, storage, chainValid, isOpen, onToggle }) => {
  const download = () => {
    const blob = new Blob([JSON.stringify(entries, null, 2)], { type: "application/json" });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = `decision-ledger-${Date.now()}.json`;
    a.click();
    URL.revokeObjectURL(url);
  };

  return (
    <>
      <button
        onClick={onToggle}
        aria-expanded={isOpen}
        className="flex w-full items-center justify-between gap-2 border-t border-terminal-subtle px-3 py-2 text-[10px] uppercase tracking-wider text-ink-muted transition-colors hover:text-ink-primary"
      >
        <span className="flex items-center gap-1.5">
          <Lock className="h-3 w-3" aria-hidden /> Decision log ({entries.length})
        </span>
        <span className="flex items-center gap-1.5 normal-case tracking-normal">
          {storage === "server" ? (chainValid ? "server ledger · chain verified" : "server ledger · CHAIN BROKEN") : "saved in this browser only"}
          <ChevronDown className={`h-3.5 w-3.5 transition-transform ${isOpen ? "rotate-180" : ""}`} />
        </span>
      </button>
      {isOpen && (
        <div className="space-y-2 px-3 pb-3">
          {entries.length === 0 ? (
            <p className="text-[10px] text-ink-muted">No decisions recorded on this finding yet.</p>
          ) : (
            <>
              <div className="flex justify-end">
                <button onClick={download} className="flex items-center gap-1 rounded border border-terminal-subtle px-2 py-0.5 font-mono text-[9px] text-ink-muted transition-colors hover:text-ink-primary">
                  <Download className="h-2.5 w-2.5" /> Download JSON
                </button>
              </div>
              <ol className="max-h-48 space-y-1.5 overflow-y-auto pr-1">
                {entries.map((e) => (
                  <li key={e.hash} className="space-y-1 rounded-md border border-terminal-subtle bg-canvas-dark px-2.5 py-2">
                    <div className="flex flex-wrap items-center justify-between gap-1.5">
                      <span className={`rounded border px-1.5 py-0.5 text-[9px] font-bold uppercase tracking-wider ${ACTION_STYLE[e.action] ?? ""}`}>
                        {e.action.replace("_", " ")}
                        {e.override_value ? ` → ${e.override_value}` : ""}
                      </span>
                      <span className="text-[9px] tabular-nums text-ink-muted">{new Date(e.ts).toLocaleString()}</span>
                    </div>
                    <div className="text-[10px] text-ink-secondary">{e.reason}</div>
                    <div className="font-mono text-[9px] text-ink-faint" title={`prev ${e.prev_hash}`}>
                      #{e.seq} · {short(e.hash, 10, 6)}
                    </div>
                  </li>
                ))}
              </ol>
            </>
          )}
        </div>
      )}
    </>
  );
};

export interface ProvenanceCockpitProps {
  discrepancy: Discrepancy | null;
}

/** Per-finding provenance, contestable override and the decision log. */
export const ProvenanceCockpit: React.FC<ProvenanceCockpitProps> = ({ discrepancy }) => {
  const { applyResolution, ledgerEntries, ledgerStorage, ledgerChainValid } = usePreIngestFirewall();
  const [isOverrideOpen, setIsOverrideOpen] = useState<boolean>(false);
  const [isLedgerOpen, setIsLedgerOpen] = useState<boolean>(false);
  if (!discrepancy) return null;

  const isGated = discrepancy.confidence < CONFIDENCE_GATE;
  const entries = ledgerEntries.filter((e) => e.finding_id === discrepancy.id);
  const btn =
    "flex items-center gap-1.5 rounded-md border px-2.5 py-1.5 text-[10px] font-bold uppercase tracking-wider transition-colors";

  return (
    <div className={`mb-3.5 rounded-xl bg-terminal-slate font-mono text-xs ${isGated ? "border border-dashed border-status-amber/70" : "border border-terminal-subtle"}`}>
      <div className="flex items-center justify-between gap-2 border-b border-terminal-subtle px-3 py-2">
        <span className="flex items-center gap-1.5 text-[10px] font-bold uppercase tracking-wider text-ink-secondary">
          <ShieldCheck className="h-3.5 w-3.5 text-cobalt-400" aria-hidden /> Decision provenance
        </span>
        <span className={`rounded-md border px-1.5 py-0.5 text-[10px] font-bold uppercase tracking-wider ${isGated ? "border-status-amber/50 text-ink-amber" : "border-status-emerald/50 text-ink-emerald"}`}>
          {isGated ? "Needs human review" : "High confidence"}
        </span>
      </div>

      <DecisionProvenanceCard discrepancy={discrepancy} />

      <div className="flex flex-wrap items-center gap-1.5 px-3 pb-3">
        <button onClick={() => applyResolution(discrepancy.id, "approve_clean", "Finding accepted")} className={`${btn} border-status-emerald/50 text-ink-emerald hover:bg-status-emerald/10`}>
          <CheckCircle2 className="h-3 w-3" aria-hidden /> Accept
        </button>
        <button onClick={() => setIsOverrideOpen((o) => !o)} aria-expanded={isOverrideOpen} className={`${btn} border-terminal-subtle bg-terminal-elevated text-ink-primary hover:bg-terminal-border`}>
          <AlertTriangle className="h-3 w-3 text-ink-amber" aria-hidden /> Override HTS
        </button>
        <button onClick={() => applyResolution(discrepancy.id, "escalate_broker", "Escalated to licensed broker / counsel")} className={`${btn} border-terminal-subtle bg-terminal-elevated text-ink-primary hover:bg-terminal-border`}>
          <Scale className="h-3 w-3 text-ink-crimson" aria-hidden /> Escalate
        </button>
      </div>

      <ContestableOverridePanel
        isOpen={isOverrideOpen}
        onClose={() => setIsOverrideOpen(false)}
        onCommit={(code, justification, memo) => {
          applyResolution(discrepancy.id, "override_hts", justification, memo || undefined, code);
          setIsOverrideOpen(false);
        }}
      />

      <DecisionLedgerLog
        entries={entries}
        storage={ledgerStorage}
        chainValid={ledgerChainValid}
        isOpen={isLedgerOpen}
        onToggle={() => setIsLedgerOpen((o) => !o)}
      />
    </div>
  );
};
