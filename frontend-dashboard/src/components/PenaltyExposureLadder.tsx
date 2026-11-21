"use client";

import React, { useState } from "react";
import { Scale, ShieldAlert } from "lucide-react";
import { sound } from "@/lib/audio";
import { TabularAmount } from "./TabularAmount";
import type { Discrepancy } from "@/lib/types";

type Tier = "negligence" | "gross_negligence" | "fraud";

interface PenaltyExposureLadderProps {
  /** The 19 U.S.C. § 1592 finding from the engine (disc-c1-03). */
  finding?: Discrepancy | null;
}

const TIERS: Record<Tier, { label: string; statute: string; rule: string; description: string; pd: string; bar: string }> = {
  negligence: {
    label: "Negligence",
    statute: "19 U.S.C. § 1592(c)(3)",
    rule: "Lesser of domestic value or 2× the loss of duty (20% of dutiable value if no loss)",
    description: "Failure to exercise reasonable care.",
    pd: "After a valid prior disclosure: interest on the loss of duty, plus tender of the loss itself.",
    bar: "bg-status-amber",
  },
  gross_negligence: {
    label: "Gross negligence",
    statute: "19 U.S.C. § 1592(c)(2)",
    rule: "Lesser of domestic value or 4× the loss of duty (40% of dutiable value if no loss)",
    description: "Actual knowledge of, or wanton disregard for, the relevant facts and obligations.",
    pd: "After a valid prior disclosure: interest on the loss of duty, plus tender of the loss itself.",
    bar: "bg-orange-500",
  },
  fraud: {
    label: "Fraud",
    statute: "19 U.S.C. § 1592(c)(1)",
    rule: "Up to the domestic value of the merchandise",
    description: "A knowing, voluntary and deliberate violation.",
    pd: "After a valid prior disclosure: up to 100% of the loss of duty (10% of dutiable value if no loss).",
    bar: "bg-status-crimson",
  },
};

export const PenaltyExposureLadder: React.FC<PenaltyExposureLadderProps> = ({ finding }) => {
  const [tier, setTier] = useState<Tier>("negligence");
  const m = finding?.metadata ?? {};
  const maxima: Record<string, string | null> = m.statutory_max_by_culpability ?? {};

  if (!finding || !m.duty_loss) {
    return (
      <div className="mt-4 rounded-lg border border-terminal-subtle bg-terminal-slate p-4 type-body-dense text-ink-muted">
        No 19 U.S.C. § 1592 finding on this document, so there is no penalty ladder to show.
      </div>
    );
  }

  const values = (Object.keys(TIERS) as Tier[]).map((t) => Number(maxima[t] ?? 0));
  const ceiling = Math.max(...values, 1);
  const active = TIERS[tier];
  const activeMax = maxima[tier];

  return (
    <div className="mt-4 rounded-lg border border-terminal-subtle bg-terminal-slate p-4 font-mono text-ink-primary">
      <div className="mb-3 flex flex-wrap items-center justify-between gap-2 border-b border-terminal-subtle pb-3">
        <div className="flex items-center gap-2">
          <Scale className="h-4 w-4 text-ink-crimson" aria-hidden />
          <span className="type-mono-data font-medium uppercase">19 U.S.C. § 1592 statutory maximums</span>
        </div>
        <span className="type-caption-mono text-ink-muted">
          Loss of duty <TabularAmount value={m.duty_loss} />
          {m.domestic_value ? (
            <>
              {" "}· domestic value <TabularAmount value={m.domestic_value} />
            </>
          ) : (
            " · domestic value not stated (cap not applied)"
          )}
        </span>
      </div>

      <div role="tablist" aria-label="Culpability" className="mb-4 grid grid-cols-3 gap-1.5 rounded border border-terminal-subtle bg-canvas-dark p-1">
        {(Object.keys(TIERS) as Tier[]).map((t) => (
          <button
            key={t}
            role="tab"
            aria-selected={tier === t}
            onClick={() => {
              sound.playTick();
              setTier(t);
            }}
            className={`rounded px-1 py-2 text-center type-caption-mono font-medium uppercase transition-colors ${
              tier === t ? "bg-terminal-elevated text-ink-primary" : "text-ink-muted hover:text-ink-primary"
            }`}
          >
            {TIERS[t].label}
          </button>
        ))}
      </div>

      <div className="mb-4 space-y-1.5" aria-hidden>
        {(Object.keys(TIERS) as Tier[]).map((t, i) => (
          <div key={t} className="flex items-center gap-2">
            <span className="w-28 shrink-0 type-caption-mono text-ink-muted">{TIERS[t].label}</span>
            <div className="h-2 flex-1 overflow-hidden rounded-full bg-canvas-dark">
              <div
                className={`h-full transition-[width] duration-300 ${TIERS[t].bar} ${tier === t ? "" : "opacity-40"}`}
                style={{ width: `${(values[i] / ceiling) * 100}%` }}
              />
            </div>
          </div>
        ))}
      </div>

      <div className="mb-3 rounded border border-terminal-subtle bg-canvas-dark/60 p-3">
        <div className="mb-1 flex flex-wrap items-center justify-between gap-1">
          <span className="statutory-cite text-[13px] text-ink-statutory">{active.statute}</span>
          <span className="type-caption-mono text-ink-muted">{active.rule}</span>
        </div>
        <div className="flex items-baseline gap-2">
          <span className="type-display-lg font-mono tabular-nums text-ink-crimson">
            {activeMax ? <TabularAmount value={activeMax} /> : "n/a"}
          </span>
          <span className="type-caption-mono text-ink-muted">{activeMax ? "statutory maximum" : "needs the domestic value"}</span>
        </div>
        <p className="mt-1 type-body-dense text-ink-secondary">{active.description}</p>
      </div>

      <div className="rounded border border-terminal-subtle bg-canvas-dark/80 p-2.5">
        <div className="mb-1 flex items-center gap-1.5 type-caption-mono font-medium uppercase text-ink-cobalt">
          <ShieldAlert className="h-3.5 w-3.5" aria-hidden /> Prior disclosure (19 CFR 162.74)
        </div>
        <p className="type-body-dense text-ink-secondary">{active.pd}</p>
        <p className="mt-1 type-caption-mono text-ink-faint">
          Maximums only. CBP mitigation guidelines (19 CFR Part 171, App. B) usually assess less; culpability is a legal
          determination.
        </p>
      </div>
    </div>
  );
};
