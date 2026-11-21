"use client";

import React from "react";
import { AlertTriangle, CheckCircle2 } from "lucide-react";
import { TabularAmount } from "./TabularAmount";
import type { AuditResult } from "@/lib/types";
import { parseCents } from "@/lib/money";

interface BilledVsLawfulDiffProps {
  audit: AuditResult | null;
}

const cents = (v: unknown): number => (v === null || v === undefined || v === "" ? 0 : Number(parseCents(v as string)));
const dollars = (c: number) => (c / 100).toFixed(2);
const usd = (c: number) => (c / 100).toLocaleString("en-US", { style: "currency", currency: "USD" });

interface Summary {
  title: string;
  cite: string;
  leftLabel: string;
  leftNote: string;
  left: number;
  rightLabel: string;
  rightNote: string;
  right: number;
  footer: string;
  tone: "loss" | "gain" | "clean";
}

/** Two-column "as billed vs reconciled" summary, computed from the audit payload. */
function summarise(audit: AuditResult): Summary | null {
  const d = audit.extracted_data ?? {};
  const findings = audit.discrepancies;

  if (Array.isArray(d.items) && d.items.length > 0) {
    const stated = d.items.reduce((s: number, it: Record<string, unknown>) => s + cents(it.stated_total), 0);
    const recalculated = d.items.reduce(
      (s: number, it: Record<string, unknown>) => s + Math.round(Number(it.quantity) * cents(it.unit_price)),
      0
    );
    const cif = String(d.incoterms ?? "").toUpperCase().startsWith("CIF");
    const nonDutiable = cif ? cents(d.freight_charge) + cents(d.insurance_charge) : 0;
    const left = stated + nonDutiable;
    const mathFindings = findings.filter((f) => f.id.startsWith("disc-c1-02")).length;
    const clean = left === recalculated && findings.length === 0;
    return {
      title: "Invoice total vs reconciled goods value",
      cite: "19 U.S.C. § 1401a",
      leftLabel: "As invoiced",
      leftNote: cif ? `Line totals + ${usd(nonDutiable)} CIF freight/insurance` : "Sum of stated line totals",
      left,
      rightLabel: "Reconciled",
      rightNote: "Quantity × unit price, freight and insurance excluded",
      right: recalculated,
      footer: clean
        ? "No valuation differences found on this invoice."
        : `${mathFindings} arithmetic error${mathFindings === 1 ? "" : "s"}${cif ? ", CIF charges deducted" : ""}. Difference ${usd(left - recalculated)}.`,
      tone: clean ? "clean" : "loss",
    };
  }

  if (d.base_freight !== undefined && audit.concept_id === "concept_2_freight") {
    const base = cents(d.base_freight);
    const fsc = Math.round(base * Number(d.billed_fsc_rate ?? 0));
    const billed = base + fsc + cents(d.chassis_split_fee) + cents(d.detention_billed);
    const notOwed = cents(audit.metrics.carrier_overbilling_caught);
    return {
      title: "Audited charges vs amount owed",
      cite: "Service contract / 46 CFR Part 541",
      leftLabel: "Billed (audited lines)",
      leftNote: "Base + fuel surcharge + chassis + detention",
      left: billed,
      rightLabel: "Owed",
      rightNote: "After disputed lines are removed",
      right: billed - notOwed,
      footer: `${usd(notOwed)} disputed across ${findings.filter((f) => cents(f.exposure_amount) > 0).length} line(s).`,
      tone: notOwed > 0 ? "loss" : "clean",
    };
  }

  if (d.duties_paid !== undefined && audit.concept_id === "concept_3_drawback") {
    const refund = cents(audit.metrics.drawback_unclaimed_unlocked);
    return {
      title: "Duties paid vs drawback refundable",
      cite: "19 U.S.C. § 1313(j)",
      leftLabel: "Duties paid on import",
      leftNote: `Entry ${d.import_entry ?? "not stated"}`,
      left: cents(d.duties_paid),
      rightLabel: "Refundable",
      rightNote: "99% of duties on matched, timely units",
      right: refund,
      footer: refund > 0 ? "Eligible for a drawback claim filed by a licensed broker or self-filer." : "No refund established from this document.",
      tone: refund > 0 ? "gain" : "clean",
    };
  }
  return null;
}

export const BilledVsLawfulDiff: React.FC<BilledVsLawfulDiffProps> = ({ audit }) => {
  if (!audit) return null;
  if (audit.source === "client") {
    return (
      <div className="my-3 rounded-lg border border-status-amber/40 bg-terminal-slate p-3 font-mono type-caption-mono text-ink-secondary">
        <span className="font-medium text-ink-amber">Browser keyword scan.</span> No amounts are computed without the backend.
      </div>
    );
  }
  const s = summarise(audit);
  if (!s) return null;

  const leftTone = s.tone === "loss" ? "text-ink-crimson" : "text-ink-numeric";
  const rightTone = s.tone === "clean" ? "text-ink-numeric" : "text-ink-emerald";

  return (
    <div className="my-3 rounded-lg border border-terminal-subtle bg-terminal-slate p-3.5 font-mono text-ink-primary">
      <div className="mb-2 flex flex-wrap items-center justify-between gap-1 border-b border-terminal-subtle pb-2 type-caption-mono uppercase text-ink-muted">
        <span className="font-medium text-ink-secondary">{s.title}</span>
        <span className="statutory-cite text-[12px] normal-case text-ink-cobalt">{s.cite}</span>
      </div>
      <div className="grid grid-cols-2 gap-2 type-mono-data">
        {[
          { label: s.leftLabel, note: s.leftNote, value: s.left, tone: leftTone },
          { label: s.rightLabel, note: s.rightNote, value: s.right, tone: rightTone },
        ].map((col) => (
          <div key={col.label} className="rounded-md border border-terminal-subtle bg-canvas-dark/60 p-2.5">
            <div className="mb-1 type-caption-mono font-medium uppercase text-ink-muted">{col.label}</div>
            <div className={`text-sm font-semibold tabular-nums ${col.tone}`}>
              <TabularAmount value={dollars(col.value)} />
            </div>
            <div className="mt-1 type-caption-mono leading-tight text-ink-muted">{col.note}</div>
          </div>
        ))}
      </div>
      <div className="mt-2.5 flex items-center gap-1.5 type-caption-mono text-ink-secondary">
        {s.tone === "clean" ? (
          <CheckCircle2 className="h-3.5 w-3.5 text-ink-emerald" aria-hidden />
        ) : (
          <AlertTriangle className={`h-3.5 w-3.5 ${s.tone === "gain" ? "text-ink-emerald" : "text-ink-amber"}`} aria-hidden />
        )}
        <span>{s.footer}</span>
      </div>
    </div>
  );
};
