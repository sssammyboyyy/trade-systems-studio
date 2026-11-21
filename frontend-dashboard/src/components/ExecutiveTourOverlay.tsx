"use client";

import React, { useState, useEffect } from "react";
import { motion } from "framer-motion";
import { X, ChevronRight, ChevronLeft } from "lucide-react";
import { sound } from "@/lib/audio";
import { BENCHMARK, VERIFIED_PYTEST_COUNT, fmtRate } from "@/lib/metrics";

interface TourStep {
  id: string;
  targetId?: string;
  title: string;
  badge: string;
  description: string;
  statute: string;
  actionHint: string;
}

const TOUR_STEPS: TourStep[] = [
  {
    id: "step-1",
    targetId: "audit-workspace",
    title: "Multi-Pillar Trade Intelligence",
    badge: "01 / ARCHITECTURE",
    description: "Toggle seamlessly across 6 enterprise compliance engines: Customs § 1592 Defense, Pre-Payment Freight Audit, Duty Drawback, OFAC 50% Sanctions Graph, HTS Copilot, and GAAP Assist Registers.",
    statute: "WCO GRI 1 to 6 • 19 U.S.C. § 1592 • 31 CFR § 501",
    actionHint: "Click any tab in the top switcher to activate that diagnostic lens.",
  },
  {
    id: "step-2",
    targetId: "audit-workspace",
    title: "Normalized Coordinate Space [0, 1000)",
    badge: "02 / LOCAL TEXT LAYER",
    description: "Powered by local pypdf text-layer parsing; findings are anchored to text found in the document itself. Bounding boxes are mathematically normalized so highlights stay locked onto canvas text regardless of display zoom or device scale.",
    statute: "Formula: left = x_norm × scale × (W_base / 1000)",
    actionHint: "Inspect the rendered PDF on the left; highlights stay aligned across zoom levels.",
  },
  {
    id: "step-3",
    targetId: "audit-workspace",
    title: "Interactive Discrepancy & Statutory Gating",
    badge: "03 / STATUTORY REASONING",
    description: "Hovering over any finding card smoothly animates and highlights the exact source text on the PDF. Extractions with confidence < 0.85 render with dashed amber borders to cue human broker review.",
    statute: "Element-Wise Confidence Gating (Conf(e) < 0.85)",
    actionHint: "Hover over discrepancy cards to see synchronized canvas bounding box illumination.",
  },
  {
    id: "step-4",
    targetId: "audit-workspace",
    title: "3-Way Document Fixture Switcher",
    badge: "04 / BASELINE VERIFICATION",
    description: "Experience both sides of the coin: test 'Corrupted Nightmare Mode' to intercept statutory penalties, switch to 'Clean Production Mode' to verify a clean FOB commercial baseline, or drop your own PDF for a local browser heuristic inspection.",
    statute: "Local Client-Side Pattern Matcher (Demonstration Heuristic Inspection)",
    actionHint: "Use the top mode pills to test Nightmare vs Clean FOB vs Client Upload.",
  },
  {
    id: "step-5",
    targetId: "audit-workspace",
    title: `Verifiable Proof: ${VERIFIED_PYTEST_COUNT}/${VERIFIED_PYTEST_COUNT} Tests & API Playground`,
    badge: "05 / PRODUCTION RIGOR",
    description: `Every financial and customs formula is backed by 100% Python Decimal precision. Inspect ${VERIFIED_PYTEST_COUNT} passing Pytest suites, review two-tier 6.5k evals/sec core & <60ms real PDF benchmarks, and simulate live REST requests in the API Playground.`,
    statute: `${fmtRate(BENCHMARK.tier2_evals_per_sec)} rule evals/sec • ${BENCHMARK.tier1_p99_ms} ms p99 per 2-page PDF • Decimal arithmetic`,
    actionHint: "Click 'Architecture & Tests' in the header to run live API simulations and inspect architecture decision records.",
  },
];

interface ExecutiveTourOverlayProps {
  isActive: boolean;
  onClose: () => void;
  onOpenArchitectureModal: () => void;
}

export const ExecutiveTourOverlay: React.FC<ExecutiveTourOverlayProps> = ({
  isActive,
  onClose,
  onOpenArchitectureModal,
}) => {
  const [currentStepIdx, setCurrentStepIdx] = useState<number>(0);

  useEffect(() => {
    if (isActive) {
      setCurrentStepIdx(0);
      sound.playSuccess();
    }
  }, [isActive]);

  if (!isActive) return null;

  const currentStep = TOUR_STEPS[currentStepIdx];
  const isFirst = currentStepIdx === 0;
  const isLast = currentStepIdx === TOUR_STEPS.length - 1;

  const handleNext = () => {
    sound.playTick();
    if (isLast) {
      onClose();
    } else {
      setCurrentStepIdx((prev) => prev + 1);
    }
  };

  const handlePrev = () => {
    sound.playTick();
    if (!isFirst) {
      setCurrentStepIdx((prev) => prev - 1);
    }
  };

  return (
    <div 
      className="fixed inset-0 z-50 flex items-end sm:items-center justify-center p-4 sm:p-6 bg-slate-950/70 backdrop-blur-[2px] animate-in fade-in duration-200"
      onClick={(e) => {
        if (e.target === e.currentTarget) {
          sound.playTick();
          onClose();
        }
      }}
    >
      <motion.div
        key={currentStep.id}
        initial={{ opacity: 0, y: 16, scale: 0.98 }}
        animate={{ opacity: 1, y: 0, scale: 1 }}
        exit={{ opacity: 0, y: -16, scale: 0.98 }}
        transition={{ duration: 0.2 }}
        className="w-full max-w-xl bg-terminal-slate text-canvas-stone border-2 border-cyan-500/60 rounded-xl shadow-2xl shadow-cyan-950/50 overflow-hidden flex flex-col font-mono"
      >
        {/* Tour Header */}
        <div className="p-4 bg-terminal-slate border-b border-terminal-subtle flex items-center justify-between">
          <div className="flex items-center gap-2">
            <span className="w-2 h-2 rounded-full bg-cyan-400 animate-pulse" />
            <span className="text-[10px] font-bold uppercase tracking-wider text-cyan-400">
              60-Second Executive Walkthrough
            </span>
            <span className="text-slate-400 text-xs">•</span>
            <span className="text-xs text-slate-300 font-semibold">
              Step {currentStepIdx + 1} of {TOUR_STEPS.length}
            </span>
          </div>

          <button
            onClick={() => {
              sound.playTick();
              onClose();
            }}
            className="p-1 text-slate-400 hover:text-ink-primary rounded hover:bg-slate-800 transition-colors"
            title="Exit Tour"
          >
            <X className="w-4 h-4" />
          </button>
        </div>

        {/* Tour Body */}
        <div className="p-5 space-y-3.5">
          <div className="flex items-center justify-between">
            <span className="px-2 py-0.5 rounded text-[10px] bg-cyan-500/10 text-cyan-400 border border-cyan-500/30 font-bold">
              {currentStep.badge}
            </span>
            <span className="text-[11px] text-amber-400 font-medium">
              {currentStep.statute}
            </span>
          </div>

          <h3 className="text-base font-bold text-ink-primary font-sans">
            {currentStep.title}
          </h3>

          <p className="text-xs text-slate-300 leading-relaxed font-sans">
            {currentStep.description}
          </p>

          <div className="p-2.5 rounded bg-canvas-dark border border-slate-800 text-[11px] text-emerald-400 flex items-center gap-2">
            <span>{currentStep.actionHint}</span>
          </div>
        </div>

        {/* Tour Footer / Action Bar */}
        <div className="p-3.5 bg-terminal-slate border-t border-terminal-subtle flex items-center justify-between gap-3">
          {/* Progress dots */}
          <div className="flex items-center gap-1.5">
            {TOUR_STEPS.map((_, idx) => (
              <button
                key={idx}
                onClick={() => {
                  sound.playTick();
                  setCurrentStepIdx(idx);
                }}
                className={`h-1.5 rounded-full transition-all ${
                  idx === currentStepIdx
                    ? "w-6 bg-cyan-400"
                    : "w-2 bg-slate-700 hover:bg-slate-500"
                }`}
                title={`Go to step ${idx + 1}`}
              />
            ))}
          </div>

          <div className="flex items-center gap-2">
            {!isFirst && (
              <button
                onClick={handlePrev}
                data-testid="tour-prev-btn"
                className="px-3 py-1.5 rounded bg-terminal-slate hover:bg-slate-800 text-slate-300 text-xs border border-terminal-subtle transition-all flex items-center gap-1"
              >
                <ChevronLeft className="w-3.5 h-3.5" />
                <span>Back</span>
              </button>
            )}

            {isLast ? (
              <div className="flex items-center gap-2">
                <button
                  onClick={() => {
                    sound.playTick();
                    onClose();
                    onOpenArchitectureModal();
                  }}
                  data-testid="tour-finish-arch-btn"
                  className="px-3.5 py-1.5 rounded bg-emerald-500 hover:bg-emerald-400 text-black text-xs font-bold uppercase tracking-wider transition-all shadow-lg shadow-emerald-950/40"
                >
                  Open Architecture Proof
                </button>
                <button
                  onClick={onClose}
                  data-testid="tour-finish-btn"
                  className="px-3 py-1.5 rounded bg-cyan-500 hover:bg-cyan-400 text-black text-xs font-bold uppercase tracking-wider transition-all"
                >
                  Finish
                </button>
              </div>
            ) : (
              <button
                onClick={handleNext}
                data-testid="tour-next-btn"
                className="px-4 py-1.5 rounded bg-cyan-500 hover:bg-cyan-400 text-black text-xs font-bold uppercase tracking-wider transition-all flex items-center gap-1 shadow-lg shadow-cyan-950/40"
              >
                <span>Next</span>
                <ChevronRight className="w-3.5 h-3.5" />
              </button>
            )}
          </div>
        </div>
      </motion.div>
    </div>
  );
};
