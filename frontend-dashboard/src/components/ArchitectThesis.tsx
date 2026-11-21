"use client";

import React from "react";
import { ArrowRight } from "lucide-react";

interface ArchitectThesisProps {
  onOpenReview: () => void;
}

export const ArchitectThesis: React.FC<ArchitectThesisProps> = ({
  onOpenReview,
}) => {
  return (
    <div className="w-full max-w-full overflow-hidden my-4 bg-terminal-slate border border-slate-800 rounded-2xl p-4 sm:p-6 lg:p-8">
      <div className="max-w-4xl mx-auto">
        {/* Author Header */}
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 pb-4 mb-6 border-b border-slate-800">
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 rounded-xl bg-blue-950 border border-blue-800/80 text-blue-400 flex items-center justify-center font-bold text-sm shadow-sm">
              SR
            </div>
            <div>
              <div className="flex flex-wrap items-center gap-x-2 gap-y-0.5">
                <span className="font-bold text-slate-100 text-sm">SAMUEL RENCKEN</span>
                <span className="text-[11px] text-emerald-400 font-semibold">Principal Trade Systems Architect</span>
              </div>
              <p className="text-[11px] text-blue-400 font-mono mt-0.5 font-medium">
                Bachelor of Commerce in Economic Sciences (International Trade) | North-West University (NWU)
              </p>
              <p className="text-[11px] text-slate-400 mt-0.5">
                Specializing in Autonomous Document Pipelines, Customs Compliance, and CargoWise eAdaptor Infrastructure
              </p>
            </div>
          </div>

          <div className="flex items-center gap-2 shrink-0">
            <span className="text-[10px] px-2 py-0.5 rounded-md bg-emerald-500/10 text-emerald-400 border border-emerald-500/20 font-semibold">
              Open to Principal Architecture Roles &amp; Systems Sprints
            </span>
          </div>
        </div>

        {/* First-Person Conversational Thesis */}
        <div className="space-y-3.5 type-body-default text-ink-secondary font-sans mb-8">
          <h2 className="type-heading-sm text-ink-primary">
            Why I Built Trade Systems Studio:
          </h2>
          <p>
            When I started auditing cross-border commercial invoices and carrier freight bills, I noticed a dangerous pattern: logistics teams were plugging raw LLM wrappers directly into customs workflows.
          </p>
          <p>
            Holding a Bachelor of Commerce in Economic Sciences (International Trade) from North-West University (NWU), I approached this problem from statutory first principles: international trade compliance and customs valuation are strictly deterministic state machines, not probabilistic text completions. In customs compliance, a guess on an HTS Chapter 85 subheading or an omitted CIF marine insurance declaration does not save money; it triggers catastrophic <span className="statutory-cite">19 U.S.C. § 1592</span> civil penalties up to 4.0x lawful duty loss.
          </p>
          <p>
            I built Trade Systems Studio to prove a deterministic alternative: use spatial document vision (local pypdf text-layer extraction) strictly to extract bounding box coordinates, and use deterministic Python rules engines with Python Decimal to enforce 19 CFR valuation math, WCO GRI 1 to 6 classification hierarchies, and CargoWise UniversalShipment XML schemas with zero float drift.
          </p>
          <p className="text-ink-muted type-mono-data">
            Whether you want to deploy this pre-audit firewall in front of your CargoWise instance, or bring me in to architect autonomous trade systems for your engineering scale-up, you can test the exact production code right on this page.
          </p>
        </div>

        {/* Conversion Action Bar */}
        <div className="flex flex-col sm:flex-row items-stretch sm:items-center justify-between gap-3 p-4 bg-slate-900/90 rounded-xl border border-slate-800">
          <div>
            <span className="type-caption-mono uppercase text-ink-muted block">
              Next Step for Engineering Leaders &amp; Operators:
            </span>
            <span className="type-body-dense text-ink-primary font-medium">
              Evaluate the production kernel with the engineer who built it.
            </span>
          </div>

          <div className="flex flex-wrap items-center gap-2">
            <button
              onClick={onOpenReview}
              className="px-4 py-2 bg-cobalt-600 hover:bg-cobalt-500 text-canvas-stone font-mono text-xs font-semibold rounded-lg transition-colors flex items-center gap-1.5"
            >
              <span>Schedule Architecture Review</span>
              <ArrowRight className="w-3.5 h-3.5" />
            </button>
          </div>
        </div>
      </div>
    </div>
  );
};
