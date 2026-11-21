"use client";

import React, { useState, useEffect } from "react";
import { TabularAmount } from "./TabularAmount";
import { motion } from "framer-motion";
import { HTSClassificationResult, GRIDecisionNode } from "@/lib/types";
import { fetchHtsPreset, isOfflineMode } from "@/lib/api";
import { soundEngine } from "@/lib/audio";

interface HtsClassifierViewerProps {
  onLeadTrigger?: () => void;
}

const PRESET_OPTIONS = [
  { id: "drone_motor", label: "01 / UAV Brushless Motor + ESC", code: "8501.31.8000" },
  { id: "server_accelerator", label: "02 / AI Tensor Accelerator (ITA-1)", code: "8542.31.0001" },
  { id: "ev_battery_pack", label: "03 / LiFePO4 Battery Module (Sec 301)", code: "8507.60.0000" },
  { id: "smart_apparel_watch", label: "04 / Biometric Smartband (Gating Demo)", code: "8517.62.0050" },
];

export const HtsClassifierViewer: React.FC<HtsClassifierViewerProps> = ({ onLeadTrigger }) => {
  const [selectedPreset, setSelectedPreset] = useState<string>("drone_motor");
  const [enteredValue, setEnteredValue] = useState<number>(45000);
  const [isOceanFreight, setIsOceanFreight] = useState<boolean>(true);
  const [data, setData] = useState<HTSClassificationResult | null>(null);
  const [loading, setLoading] = useState<boolean>(true);
  const [activeStepIndex, setActiveStepIndex] = useState<number>(0);

  useEffect(() => {
    let isMounted = true;
    setLoading(true);
    fetchHtsPreset(selectedPreset, enteredValue, isOceanFreight)
      .then((res) => {
        if (isMounted) {
          setData(res);
          setLoading(false);
        }
      })
      .catch(() => {
        if (isMounted) setLoading(false);
      });

    return () => {
      isMounted = false;
    };
  }, [selectedPreset, enteredValue, isOceanFreight]);

  const handleSelectPreset = (id: string) => {
    soundEngine.click();
    setSelectedPreset(id);
    setActiveStepIndex(0);
  };

  return (
    <div aria-busy={loading} className="flex-1 flex flex-col bg-canvas-dark text-ink-primary overflow-hidden">
      {/* Top Controller Bar */}
      <div className="border-b border-terminal-subtle bg-terminal-slate/90 backdrop-blur px-6 py-4 flex flex-wrap items-center justify-between gap-4">
        <div>
          <div className="flex items-center gap-2">
            <span className="inline-block w-2.5 h-2.5 rounded-full bg-cyan-400 animate-pulse" />
            <h2 className="text-sm font-semibold tracking-wider uppercase text-cyan-400">
              Pillar 03: Autonomous HTS Classification Copilot
            </h2>
            {isOfflineMode() && (
              <span className="text-[10px] font-mono px-2 py-0.5 rounded bg-amber-500/10 text-amber-300 border border-amber-500/30">
                Offline Demo Mode
              </span>
            )}
          </div>
          <p className="text-xs text-slate-400 mt-0.5">
            Path-Dependent WCO GRI 1 to 6 Reasoning Engine with Element-Wise Confidence Gating & Decimal Landed Cost
          </p>
        </div>

        {/* Preset Selector */}
        <div className="flex items-center gap-2 flex-wrap">
          {PRESET_OPTIONS.map((opt) => {
            const isActive = selectedPreset === opt.id;
            return (
              <button
                key={opt.id}
                onClick={() => handleSelectPreset(opt.id)}
                className={`px-3 py-1.5 text-xs font-mono font-medium rounded transition-all flex items-center gap-2 border ${
                  isActive
                    ? "bg-cyan-500/15 text-cyan-300 border-cyan-500/40 shadow-sm"
                    : "bg-terminal-slate text-slate-400 border-terminal-subtle hover:border-slate-600 hover:text-ink-primary"
                }`}
              >
                <span>{opt.label}</span>
                <span className="text-[10px] opacity-60 bg-canvas-dark/40 px-1 py-0.5 rounded">
                  {opt.code}
                </span>
              </button>
            );
          })}
        </div>
      </div>

      {/* Main Content Area */}
      <div className="flex-1 overflow-y-auto p-6 grid grid-cols-1 lg:grid-cols-12 gap-6">
        {/* Left Column: WCO GRI Hierarchical Decision Tree */}
        <div className="lg:col-span-8 space-y-6">
          {/* Header Card */}
          <div className="p-5 rounded-lg border border-terminal-subtle bg-terminal-slate relative overflow-hidden">
            <div className="flex flex-wrap items-start justify-between gap-4">
              <div className="space-y-1.5 max-w-xl">
                <div className="flex items-center gap-2.5">
                  <span className="px-2 py-0.5 text-[10px] font-mono tracking-widest uppercase bg-slate-800 text-slate-300 border border-slate-700 rounded">
                    Origin: {data?.country_of_origin || "CN"}
                  </span>
                  <span className="text-xs text-slate-500 font-mono">
                    ID: {data?.item_id}
                  </span>
                </div>
                <h3 className="text-base font-semibold text-ink-primary">
                  {data?.product_title || "Loading..."}
                </h3>
                <p className="text-xs text-slate-400 leading-relaxed">
                  {data?.input_description}
                </p>
              </div>

              {/* HTS Code & Confidence Badge */}
              <div className="flex flex-col items-end gap-1.5">
                <div className="text-[11px] font-mono uppercase tracking-wider text-slate-500">
                  Statutory 10-Digit HTS
                </div>
                <div
                  className={`px-3.5 py-1.5 rounded font-mono text-base font-bold tracking-wider flex items-center gap-2 ${
                    data?.requires_human_review
                      ? "border-2 border-dashed border-amber-500 bg-amber-500/10 text-amber-300 animate-pulse"
                      : "border border-emerald-500/40 bg-emerald-500/10 text-emerald-400"
                  }`}
                >
                  <span>{data?.classified_hts_code || "--------"}</span>
                  <span className="text-xs font-normal opacity-80">
                    ({((data?.confidence || 0) * 100).toFixed(0)}%)
                  </span>
                </div>

                {data?.requires_human_review && (
                  <div className="text-[11px] font-mono text-amber-400 flex items-center gap-1.5 mt-1 bg-amber-950/40 px-2 py-1 rounded border border-amber-800/40">
                    <span>⚠️</span>
                    <span>Confidence &lt; 0.85: Gated for Human Broker Review</span>
                  </div>
                )}
              </div>
            </div>
          </div>

          {/* WCO GRI Step-by-Step Path */}
          <div className="space-y-3">
            <div className="flex items-center justify-between text-xs font-mono text-slate-400 px-1">
              <span className="font-semibold uppercase tracking-wider text-slate-400">
                WCO General Rules of Interpretation (GRI) Path Trace
              </span>
              <span>{data?.gri_path.length || 0} Reasoning Steps</span>
            </div>

            <div className="space-y-3">
              {data?.gri_path.map((node: GRIDecisionNode, idx: number) => {
                const isSelected = activeStepIndex === idx;
                const isLowConfidence = node.confidence < 0.85;

                return (
                  <motion.div
                    key={idx}
                    initial={{ opacity: 0, y: 10 }}
                    animate={{ opacity: 1, y: 0 }}
                    transition={{ delay: idx * 0.08 }}
                    onClick={() => {
                      soundEngine.click();
                      setActiveStepIndex(idx);
                    }}
                    className={`p-4 rounded-lg border transition-all cursor-pointer ${
                      isSelected
                        ? "bg-terminal-elevated border-cyan-500/60 shadow-lg shadow-cyan-950/20"
                        : "bg-terminal-slate border-terminal-subtle hover:border-slate-600"
                    }`}
                  >
                    <div className="flex items-start justify-between gap-4">
                      <div className="flex items-center gap-3">
                        <div
                          className={`w-7 h-7 rounded flex items-center justify-center font-mono text-xs font-bold ${
                            isSelected
                              ? "bg-cyan-500 text-black"
                              : "bg-terminal-elevated text-slate-300"
                          }`}
                        >
                          {idx + 1}
                        </div>
                        <div>
                          <div className="flex items-center gap-2">
                            <span className="text-xs font-bold font-mono text-cyan-400">
                              {node.step_rule}
                            </span>
                            <span className="text-slate-400">|</span>
                            <span className="text-xs font-mono font-semibold text-ink-primary">
                              {node.heading_or_subheading}
                            </span>
                          </div>
                          <div className="text-xs text-slate-400 mt-0.5">
                            {node.description}
                          </div>
                        </div>
                      </div>

                      {/* Confidence Meter */}
                      <div className="flex items-center gap-2 flex-shrink-0">
                        <div className="w-16 bg-terminal-elevated h-2 rounded-full overflow-hidden">
                          <div
                            className={`h-full rounded-full ${
                              isLowConfidence ? "bg-amber-500" : "bg-emerald-500"
                            }`}
                            style={{ width: `${node.confidence * 100}%` }}
                          />
                        </div>
                        <span
                          className={`text-xs font-mono font-medium ${
                            isLowConfidence ? "text-amber-400" : "text-emerald-400"
                          }`}
                        >
                          {(node.confidence * 100).toFixed(0)}%
                        </span>
                      </div>
                    </div>

                    {/* Legal Rationale Box */}
                    <div className="mt-3 pt-3 border-t border-terminal-subtle text-xs text-slate-400 leading-relaxed">
                      <div className="font-mono text-[10px] uppercase text-slate-500 mb-1">
                        Statutory Rationale:
                      </div>
                      <p>{node.legal_rationale}</p>

                      {/* Competing Candidates Eliminated */}
                      {node.competing_candidates && node.competing_candidates.length > 0 && (
                        <div className="mt-2.5 flex items-center gap-2 flex-wrap">
                          <span className="text-[10px] font-mono text-slate-400 uppercase">
                            Eliminated Candidates:
                          </span>
                          {node.competing_candidates.map((cand, cIdx) => (
                            <span
                              key={cIdx}
                              className="text-[11px] font-mono line-through text-red-400/80 bg-red-950/20 px-2 py-0.5 rounded border border-red-900/30"
                            >
                              {cand}
                            </span>
                          ))}
                        </div>
                      )}
                    </div>
                  </motion.div>
                );
              })}
            </div>
          </div>

          {/* Section & Chapter Notes Cited */}
          <div className="p-4 rounded-lg border border-terminal-subtle bg-terminal-slate">
            <div className="text-xs font-mono font-semibold text-slate-400 uppercase tracking-wider mb-2.5 flex items-center gap-2">
              <span>🏛️</span>
              <span>Statutory Chapter & Section Notes Cited</span>
            </div>
            <div className="space-y-1.5">
              {data?.chapter_notes_cited.map((note, nIdx) => (
                <div
                  key={nIdx}
                  className="text-xs font-mono text-slate-300 bg-terminal-slate px-3 py-1.5 rounded border border-terminal-subtle flex items-center gap-2"
                >
                  <span className="text-cyan-400">§</span>
                  <span>{note}</span>
                </div>
              ))}
            </div>
          </div>
        </div>

        {/* Right Column: Deterministic Landed Cost Calculator */}
        <div className="lg:col-span-4 space-y-6">
          <div className="p-5 rounded-lg border border-terminal-subtle bg-terminal-slate space-y-5">
            <div className="flex items-center justify-between border-b border-terminal-subtle pb-3">
              <div>
                <h4 className="text-xs font-bold uppercase tracking-wider text-ink-primary">
                  Deterministic Landed Cost
                </h4>
                <div className="text-[11px] text-slate-400">
                  100% Python Decimal Financial Standard
                </div>
              </div>
              <span className="px-2 py-0.5 text-[10px] font-mono bg-emerald-500/10 text-emerald-400 border border-emerald-500/30 rounded">
                19 CFR § 24.23/24
              </span>
            </div>

            {/* Live Interactive Inputs */}
            <div className="space-y-3.5">
              <div>
                <label className="text-[11px] font-mono text-slate-400 uppercase block mb-1">
                  Entered FOB Value (USD)
                </label>
                <div className="relative">
                  <span className="absolute left-3 top-2 text-xs font-mono text-slate-400">$</span>
                  <input
                    type="number"
                    value={enteredValue}
                    onChange={(e) => setEnteredValue(Math.max(100, Number(e.target.value) || 0))}
                    className="w-full bg-canvas-dark border border-terminal-subtle rounded px-7 py-1.5 text-xs font-mono text-ink-primary focus:outline-none focus:border-cyan-500"
                  />
                </div>
              </div>

              <div className="flex items-center justify-between pt-1">
                <span className="text-xs text-slate-400">Transport Mode</span>
                <button
                  onClick={() => setIsOceanFreight(!isOceanFreight)}
                  className="px-2.5 py-1 text-xs font-mono rounded border border-terminal-subtle bg-canvas-dark hover:border-slate-500 text-slate-200"
                >
                  {isOceanFreight ? "🚢 Ocean (HMF 0.125%)" : "✈️ Air / Truck ($0 HMF)"}
                </button>
              </div>
            </div>

            {/* Itemized Landed Cost Math */}
            <div className="space-y-2.5 pt-2 border-t border-terminal-subtle type-mono-data">
              <div className="flex justify-between items-center text-ink-muted">
                <span>Entered Value:</span>
                <TabularAmount value={Number(data?.landed_cost.entered_value || 0)} className="text-ink-numeric" />
              </div>

              <div className="flex justify-between items-center text-ink-muted">
                <span>Customs Duty ({(Number(data?.landed_cost.duty_rate_ad_valorem || 0) * 100).toFixed(2)}%):</span>
                <TabularAmount value={Number(data?.landed_cost.customs_duty || 0)} className="text-ink-emerald font-medium" />
              </div>

              <div className="flex justify-between items-center text-ink-muted">
                <div className="flex items-center gap-1">
                  <span>MPF (0.3464%):</span>
                  <span className="type-caption-mono text-ink-muted">[$34.58 to $670.86]</span>
                </div>
                <TabularAmount value={Number(data?.landed_cost.mpf_fee || 0)} className="text-ink-secondary" />
              </div>

              {Number(data?.landed_cost.section_301_duty || 0) > 0 && (
                <div className="flex justify-between items-center text-ink-muted">
                  <div className="flex items-center gap-1">
                    <span className="text-amber-400">Section 301 ({(Number(data?.landed_cost.section_301_rate || 0) * 100).toFixed(1)}%):</span>
                    <span className="type-caption-mono text-amber-500/80">[{data?.landed_cost.section_301_subheading || "Ch. 99"}]</span>
                  </div>
                  <TabularAmount value={Number(data?.landed_cost.section_301_duty || 0)} className="text-amber-400 font-medium" />
                </div>
              )}

              <div className="flex justify-between items-center text-ink-muted">
                <span>Harbor Maint. (0.125%):</span>
                <TabularAmount value={Number(data?.landed_cost.hmf_fee || 0)} className="text-ink-secondary" />
              </div>

              <div className="flex justify-between items-center text-ink-muted">
                <span>Freight & Insurance:</span>
                <TabularAmount value={Number(data?.landed_cost.freight_and_insurance || 0)} className="text-ink-secondary" />
              </div>

              <div className="pt-2 border-t border-terminal-subtle flex justify-between items-center font-medium">
                <span className="text-cyan-400">Total Customs Fees:</span>
                <TabularAmount value={Number(data?.landed_cost.total_customs_cost || 0)} className="text-cyan-400 text-sm" />
              </div>

              <div className="p-3 rounded bg-canvas-dark border border-cyan-500/30 flex justify-between items-center font-medium">
                <span className="text-ink-primary type-mono-data uppercase">Total Landed Cost:</span>
                <TabularAmount value={Number(data?.landed_cost.total_landed_cost || 0)} className="text-base text-ink-emerald font-semibold" />
              </div>
            </div>

            {/* Enterprise CTA Card */}
            <div className="p-4 rounded bg-gradient-to-br from-cyan-950/30 to-canvas-dark border border-cyan-500/30 space-y-2.5">
              <div className="type-mono-data font-medium text-ink-primary flex items-center gap-1.5">
                <span>⚡</span>
                <span>Automate 10,000+ SKU Classifications</span>
              </div>
              <p className="text-[11px] text-slate-400 leading-relaxed">
                Connect your ERP catalog. Replace manual broker lag with instant, verifiable WCO GRI reasoning defensible before CBP auditors.
              </p>
              <button
                onClick={() => {
                  soundEngine.click();
                  onLeadTrigger?.();
                }}
                className="w-full py-2 px-3 rounded bg-cyan-500 hover:bg-cyan-400 text-black font-semibold text-xs tracking-wider uppercase transition-all shadow-md shadow-cyan-500/20"
              >
                Request Enterprise Pilot ($0 Upfront)
              </button>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};
