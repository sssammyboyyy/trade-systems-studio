"use client";

import React from "react";
import { ShieldCheck, CheckCircle2 } from "lucide-react";
import { IcpPersonaSwitcher, IcpPersona } from "./IcpPersonaSwitcher";
import { BENCHMARK, VERIFIED_PYTEST_COUNT, fmtRate } from "@/lib/metrics";

interface SystemsHeroSectionProps {
  persona: IcpPersona;
  onChangePersona: (p: IcpPersona) => void;
}

const LENS_COPY: Record<IcpPersona, { label: string; body: string }> = {
  cfo: {
    label: "Finance lens",
    body: "Freight overcharges and unclaimed drawback are caught before payment, with the contract clause or statute behind each line, so disputes are settled with documents rather than arguments.",
  },
  counsel: {
    label: "Counsel lens",
    body: "Every finding cites its authority and shows the statutory maximum under 19 U.S.C. § 1592(c) by culpability, capped by domestic value where it is known. Culpability itself is left to counsel.",
  },
  cto: {
    label: "Engineering lens",
    body: "No model in the arithmetic path: rules run in Python Decimal over fields read from the PDF's own text layer, missing fields quarantine the document, and each run is content-addressed by document and ruleset hash.",
  },
};

export const SystemsHeroSection: React.FC<SystemsHeroSectionProps> = ({ persona, onChangePersona }) => {
  const lens = LENS_COPY[persona];
  return (
    <section className="relative border-b border-terminal-subtle bg-terminal-slate/40 py-10 lg:py-14">
      <div className="mx-auto max-w-7xl px-4 sm:px-6 lg:px-8">
        <div className="flex flex-col gap-8 lg:flex-row lg:items-end lg:justify-between">
          <div className="max-w-3xl">
            <div className="mb-5 flex flex-wrap items-center gap-2 type-mono-data">
              <span className="inline-flex items-center gap-1.5 rounded-md border border-cobalt-800 bg-cobalt-950/80 px-2.5 py-1 font-medium text-cobalt-300">
                <ShieldCheck className="h-3.5 w-3.5 text-ink-cobalt" aria-hidden />
                <span>Pre-ingest document checks</span>
              </span>
              <span className="inline-flex items-center gap-1.5 rounded-md border border-terminal-subtle bg-terminal-elevated px-2.5 py-1 text-ink-secondary tabular-nums">
                <CheckCircle2 className="h-3.5 w-3.5 text-ink-emerald" aria-hidden />
                <span>{`${VERIFIED_PYTEST_COUNT}/${VERIFIED_PYTEST_COUNT} Automated Tests Passing`}</span>
              </span>
            </div>

            <h1 className="mb-4 text-balance text-3xl font-semibold leading-[1.12] tracking-[-0.025em] text-ink-primary sm:text-4xl lg:text-5xl">
              Catch customs, freight and drawback errors{" "}
              <span className="text-ink-cobalt">before they reach CargoWise</span>
            </h1>

            <p className="max-w-2xl type-body-default font-normal leading-relaxed text-ink-secondary sm:text-base">
              Upload a commercial invoice, freight bill, drawback claim or ownership dossier. The engine reads the
              document&apos;s own text, applies dated statutory tables, and either releases it or holds it with every
              dollar traced to a line on the page. Anything it cannot read completely is held for a broker, never
              guessed.
            </p>
          </div>

          <IcpPersonaSwitcher persona={persona} onChange={onChangePersona} />
        </div>

        <div className="mt-6 max-w-3xl border-l-2 border-cobalt-600 pl-3">
          <div className="mb-1 type-caption-mono font-medium uppercase text-ink-cobalt">{lens.label}</div>
          <p className="type-body-default text-ink-secondary">{lens.body}</p>
        </div>

        <dl className="mt-8 grid grid-cols-2 gap-3 border-t border-terminal-subtle pt-5 sm:grid-cols-4">
          {[
            {
              k: "Rule evaluations",
              v: `${fmtRate(BENCHMARK.tier2_evals_per_sec)} /s`,
              s: `p99 ${BENCHMARK.tier2_p99_ms} ms, in memory`,
            },
            {
              k: "2-page PDF audits",
              v: `${fmtRate(BENCHMARK.tier1_docs_per_sec)} /s`,
              s: `p99 ${BENCHMARK.tier1_p99_ms} ms, parse + rules`,
            },
            { k: "Arithmetic", v: "Decimal", s: "No floats, no LLM in any amount" },
            { k: "Unreadable input", v: "Held", s: "Missing fields quarantine, never default" },
          ].map((m) => (
            <div key={m.k} className="rounded-lg border border-terminal-subtle bg-terminal-slate p-3">
              <dt className="type-caption-mono uppercase text-ink-muted">{m.k}</dt>
              <dd className="font-mono text-base font-semibold tabular-nums text-ink-primary sm:text-lg">{m.v}</dd>
              <dd className="type-caption-mono text-ink-muted">{m.s}</dd>
            </div>
          ))}
        </dl>
        <p className="mt-2 type-caption-mono text-ink-faint">
          Measured {BENCHMARK.measured_on} on {BENCHMARK.hardware}; throughput is machine-dependent.
        </p>
      </div>
    </section>
  );
};
