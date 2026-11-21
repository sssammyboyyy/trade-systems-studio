"use client";

import React, { useState } from "react";
import { FileText, Cpu, CheckCircle2, ShieldCheck, ArrowRight, Code, Network } from "lucide-react";
import { VERIFIED_PYTEST_COUNT } from "@/lib/metrics";

interface PipelineStage {
  id: string;
  step: string;
  title: string;
  subtitle: string;
  icon: React.ReactNode;
  serviceFile: string;
  contract: string;
  details: string[];
}

const STAGES: PipelineStage[] = [
  {
    id: "ingest",
    step: "Stage 01",
    title: "Document Ingestion",
    subtitle: "Text-layer PDF, 5 MB / 50 pages",
    icon: <FileText className="w-4 h-4" />,
    serviceFile: "backend-engine/app/services/extractor.py",
    contract: "Stream[bytes] → RawLayoutTokens",
    details: [
      "Streamed upload with size cap, %PDF- magic-byte check and SHA-256 of the bytes",
      "Corrupt or encrypted PDFs are rejected with HTTP 422, never a 500",
      "Scans without a text layer are held for review: no OCR, nothing guessed",
    ],
  },
  {
    id: "docling",
    step: "Stage 02",
    title: "Spatial Layout Extraction",
    subtitle: "pypdf text layer + layout boxes",
    icon: <Cpu className="w-4 h-4" />,
    serviceFile: "backend-engine/app/services/layout_extractor.py",
    contract: "Normalized Coordinates [0, 1000) Space",
    details: [
      "Extracts field coordinates normalized to 1000x1000 unit space",
      "Calculates element-wise extraction confidence scores",
      "Triggers dashed visual uncertainty borders on confidence < 85%",
    ],
  },
  {
    id: "rules_engine",
    step: "Stage 03",
    title: "Deterministic Trade Math",
    subtitle: "Python Decimal Ledgers",
    icon: <CheckCircle2 className="w-4 h-4" />,
    serviceFile: "backend-engine/app/services/customs_audit.py",
    contract: "Strict Python Decimal (0% Floating Drift)",
    details: [
      "Absolute ban on LLM arithmetic (strict Decimal with ROUND_HALF_UP)",
      "19 U.S.C. § 1592 civil fraud & negligence penalty ladders",
      "Detention free-time and 46 CFR Part 541 billing checks",
    ],
  },
  {
    id: "graph_engine",
    step: "Stage 04",
    title: "Sanctions & Valuation Graph",
    subtitle: "OFAC 50% Rule & Assists",
    icon: <Network className="w-4 h-4" />,
    serviceFile: "backend-engine/app/services/sanctions_screener.py",
    contract: "Recursive Graph Traversal + RapidFuzz C++",
    details: [
      "RapidFuzz C++ fuzzy matching against OpenSanctions watchlists",
      "Traverses corporate beneficial ownership per OFAC 50% Rule",
      "19 CFR § 152.103 assist amortization & CIF insurance apportionment",
    ],
  },
  {
    id: "cargowise_relay",
    step: "Stage 05",
    title: "CargoWise eAdaptor Relay",
    subtitle: "UniversalShipment XML v1.1",
    icon: <ShieldCheck className="w-4 h-4" />,
    serviceFile: "backend-engine/app/services/cargowise_xml.py",
    contract: "UniversalInterchange XML Schema 2011/11",
    details: [
      "Formats clean UniversalShipment XML ready for eAdaptor HTTP+XML POST",
      "Injects pre-audit verification status and mitigated penalty tags",
      "Provides raw vs. reconciled line-level diff highlighting",
    ],
  },
];

export const InlineArchitectureFlow: React.FC = () => {
  const [activeStage, setActiveStage] = useState<PipelineStage>(STAGES[2]);

  return (
    <div className="w-full max-w-full overflow-hidden my-4 bg-terminal-slate border border-slate-800 rounded-2xl p-4 sm:p-6 font-mono">
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-3 pb-4 mb-6 border-b border-slate-800">
        <div>
          <div className="flex items-center gap-2">
            <span className="text-xs font-bold text-blue-400 uppercase tracking-wider">
              System Architecture &amp; Data Pipeline
            </span>
            <span className="text-[10px] px-2 py-0.5 rounded-md bg-emerald-500/10 text-emerald-400 border border-emerald-500/20 font-semibold">
              {`${VERIFIED_PYTEST_COUNT}/${VERIFIED_PYTEST_COUNT} Verified Automated Tests`}
            </span>
          </div>
          <h2 className="type-display-md text-ink-primary mt-1 font-sans">
            Deterministic Pre-Ingest Verification Kernel
          </h2>
        </div>
        <p className="text-xs text-slate-400 max-w-md">
          Coupling spatial document extraction with deterministic Python rules. Click any pipeline stage to inspect underlying service files and contracts.
        </p>
      </div>

      {/* 5-Stage Horizontal Flow Cards */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-5 gap-2 mb-6">
        {STAGES.map((stage, idx) => {
          const isSelected = activeStage.id === stage.id;
          return (
            <button
              key={stage.id}
              onClick={() => setActiveStage(stage)}
              className={`p-3 rounded-xl border text-left transition-colors flex flex-col justify-between gap-2 relative ${
                isSelected
                  ? "bg-slate-800/90 border-blue-500 ring-1 ring-blue-500/50 shadow-md"
                  : "bg-slate-900/60 hover:bg-slate-800/50 border-slate-800/90"
              }`}
            >
              <div>
                <div className="flex items-center justify-between text-[10px] text-slate-400 mb-1">
                  <span>{stage.step}</span>
                  {stage.icon}
                </div>
                <div className="text-xs font-bold text-slate-100 leading-snug">
                  {stage.title}
                </div>
                <div className="text-[10px] text-slate-400 mt-0.5">
                  {stage.subtitle}
                </div>
              </div>
              {idx < STAGES.length - 1 && (
                <div className="hidden lg:block absolute -right-2 top-1/2 -translate-y-1/2 z-10 pointer-events-none">
                  <ArrowRight className="w-3.5 h-3.5 text-slate-600" />
                </div>
              )}
            </button>
          );
        })}
      </div>

      {/* Deep Dive Inspection Panel for Active Stage */}
      <div className="bg-slate-950/80 border border-slate-800/80 rounded-xl p-4">
        <div className="flex flex-wrap items-center justify-between gap-2 pb-2 mb-3 border-b border-slate-800 text-xs">
          <div className="flex items-center gap-2">
            <span className="font-bold text-blue-400">{activeStage.step}:</span>
            <span className="font-bold text-slate-200">{activeStage.title}</span>
            <span className="text-slate-400">({activeStage.subtitle})</span>
          </div>
          <div className="text-[11px] text-slate-400 flex items-center gap-1.5">
            <Code className="w-3 h-3 text-slate-400" />
            <code className="text-slate-300 bg-slate-900 px-2 py-0.5 rounded-md border border-slate-800">
              {activeStage.serviceFile}
            </code>
          </div>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-2 gap-4 text-xs">
          <div>
            <span className="text-[10px] uppercase font-bold text-slate-400 block mb-1.5">
              Architectural Invariants &amp; Execution Guarantees
            </span>
            <ul className="space-y-1.5">
              {activeStage.details.map((detail, idx) => (
                <li key={idx} className="flex items-start gap-2 text-slate-300">
                  <span className="text-emerald-400 font-bold">•</span>
                  <span>{detail}</span>
                </li>
              ))}
            </ul>
          </div>
          <div className="bg-slate-900/90 p-3 rounded-lg border border-slate-800 flex flex-col justify-between">
            <div>
              <span className="text-[10px] uppercase font-bold text-slate-400 block mb-1">
                Data Transfer Contract
              </span>
              <code className="text-[11px] text-blue-300 break-all font-mono">
                {activeStage.contract}
              </code>
            </div>
            <div className="pt-2 mt-2 border-t border-slate-800/80 text-[10px] text-slate-400 flex items-center justify-between">
              <span>Deterministic Python 3.12 Engine</span>
              <span className="text-emerald-400 font-semibold">Verified in CI Test Runner</span>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};
