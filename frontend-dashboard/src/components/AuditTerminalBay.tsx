"use client";

import React from "react";
import { AuditResult, Discrepancy } from "@/lib/types";
import { DiscrepancyCard } from "./DiscrepancyCard";
import { CargoWiseXmlViewer } from "./CargoWiseXmlViewer";
import { DeveloperApiSandbox } from "./DeveloperApiSandbox";
import { ThreeWayResolutionBar } from "./ThreeWayResolutionBar";
import { ProvenanceCockpit } from "./ProvenanceCockpit";
import { BilledVsLawfulDiff } from "./BilledVsLawfulDiff";
import { sound } from "@/lib/audio";
import { resolveAssetPath } from "@/lib/assets";
import { Code2, Terminal, ExternalLink, AlertTriangle, CheckCircle2 } from "lucide-react";

interface AuditTerminalBayProps {
  activeConceptId: string;
  auditData: AuditResult | null;
  activeDiscrepancy: Discrepancy | null;
  activeDiscrepancyId: string | null;
  setActiveDiscrepancyId: (id: string | null) => void;
  handleCardClick: (id: string) => void;
  rightTerminalTab: "discrepancies" | "cargowise" | "developer_api";
  setRightTerminalTab: (tab: "discrepancies" | "cargowise" | "developer_api") => void;
  mobileTab: "doc" | "findings";
  setMobileTab: (tab: "doc" | "findings") => void;
  desktopViewMode: "split" | "doc_focus" | "report_focus";
}

export const AuditTerminalBay: React.FC<AuditTerminalBayProps> = ({
  activeConceptId,
  auditData,
  activeDiscrepancy,
  activeDiscrepancyId,
  setActiveDiscrepancyId,
  handleCardClick,
  rightTerminalTab,
  setRightTerminalTab,
  mobileTab,
  setMobileTab,
  desktopViewMode,
}) => {
  // Never substitute a fixture for a document that has no URL (e.g. an upload).
  const safePdfPath = auditData?.document_url || "";

  return (
    <div
      className={`h-full flex-col bg-terminal-slate overflow-hidden transition-all duration-200 ${
        mobileTab === "findings" ? "flex w-full" : "hidden lg:flex"
      } ${
        desktopViewMode === "report_focus"
          ? "lg:w-full lg:flex"
          : desktopViewMode === "doc_focus"
          ? "lg:hidden"
          : "lg:w-2/5"
      }`}
    >
      {/* Terminal Bay Header & Tabs */}
      <div className="px-4 py-3 bg-canvas-dark border-b border-terminal-subtle flex items-center justify-between shrink-0 font-mono text-xs">
        <div role="tablist" aria-label="Audit inspection panels" className="inline-flex p-0.5 bg-terminal-slate border border-terminal-subtle rounded-lg">
          <button
            role="tab"
            aria-selected={rightTerminalTab === "discrepancies"}
            onClick={() => {
              sound.playTick();
              setRightTerminalTab("discrepancies");
            }}
            className={`px-2.5 py-1 rounded-md type-caption-mono font-medium transition-colors ${
              rightTerminalTab === "discrepancies"
                ? "bg-cobalt-600 text-canvas-stone shadow-xs"
                : "text-ink-muted hover:text-ink-primary"
            }`}
          >
            Findings ({auditData?.discrepancies.length || 0})
          </button>

          <button
            role="tab"
            aria-selected={rightTerminalTab === "cargowise"}
            onClick={() => {
              sound.playLock();
              setRightTerminalTab("cargowise");
            }}
            className={`px-2.5 py-1 rounded-md type-caption-mono font-medium transition-colors flex items-center gap-1 ${
              rightTerminalTab === "cargowise"
                ? "bg-cobalt-600 text-canvas-stone shadow-xs"
                : "text-ink-muted hover:text-ink-primary"
            }`}
          >
            <Code2 className="w-3 h-3" />
            <span>CargoWise XML</span>
          </button>

          <button
            role="tab"
            aria-selected={rightTerminalTab === "developer_api"}
            onClick={() => {
              sound.playLock();
              setRightTerminalTab("developer_api");
            }}
            className={`px-2.5 py-1 rounded-md type-caption-mono font-medium transition-colors flex items-center gap-1 ${
              rightTerminalTab === "developer_api"
                ? "bg-cobalt-600 text-canvas-stone shadow-xs"
                : "text-ink-muted hover:text-ink-primary"
            }`}
          >
            <Terminal className="w-3 h-3" />
            <span>API Sandbox</span>
          </button>
        </div>

        {/* PDF Link */}
        {safePdfPath && (
        <a
          href={resolveAssetPath(safePdfPath)}
          target="_blank"
          rel="noreferrer"
          className="text-xs font-mono text-slate-400 hover:text-blue-400 flex items-center gap-1 border border-terminal-subtle px-2 py-1 rounded-md transition-colors"
        >
          <span>PDF</span>
          <ExternalLink className="w-3 h-3" />
        </a>
        )}
      </div>

      {/* Sub-Tab 1: Discrepancies Redline */}
      {rightTerminalTab === "discrepancies" && (
        <div className="flex-1 overflow-y-auto p-4 space-y-3.5">
          {/* Honest Disclaimer Banner for Uploaded Heuristic Scans */}
          {activeConceptId === "client_upload_audit" && (
            <div className="p-3 bg-amber-950/40 border border-amber-600/70 rounded-lg text-amber-200 text-xs font-mono flex items-start gap-2.5 shadow-sm">
              <AlertTriangle className="w-4 h-4 text-amber-400 shrink-0 mt-0.5" />
              <div className="space-y-1">
                <div className="font-bold text-amber-300 uppercase tracking-wide text-[11px]">
                  Demonstration Heuristic Inspection
                </div>
                <div className="text-[11px] leading-relaxed text-amber-200/90">
                  Demonstration heuristic pattern matcher running in browser. Does not certify compliance or replace licensed customs broker review.
                </div>
              </div>
            </div>
          )}

          <ProvenanceCockpit discrepancy={activeDiscrepancy} />

          <BilledVsLawfulDiff audit={auditData} />

          {activeConceptId === "concept_clean_fob" ? (
            <div className="p-4 bg-emerald-950/20 border border-emerald-800/60 rounded-lg font-mono space-y-4">
              <div className="flex items-center gap-3">
                <div className="w-9 h-9 rounded-md bg-emerald-950 border border-emerald-600 text-emerald-400 flex items-center justify-center shrink-0 shadow-xs">
                  <CheckCircle2 className="w-5 h-5" />
                </div>
                <div>
                  <div className="text-xs font-bold text-emerald-400 uppercase tracking-wider flex items-center gap-2">
                    <span>Clean Commercial Baseline</span>
                    <span className="text-[10px] px-1.5 py-0.5 bg-emerald-900/60 border border-emerald-700 text-emerald-300 rounded-sm">
                      BASELINE VERIFIED
                    </span>
                  </div>
                  <div className="text-[11px] text-slate-400 mt-0.5">
                    Standard FOB commercial invoice with verified non-dutiable terms and zero flagged defects.
                  </div>
                </div>
              </div>

              <div className="p-3 bg-canvas-dark border border-emerald-900/40 rounded-md space-y-2 text-xs">
                <div className="flex items-center justify-between text-slate-300 pb-1.5 border-b border-terminal-subtle">
                  <span className="text-slate-400">19 U.S.C. § 1592 Penalty Exposure:</span>
                  <span className="font-bold text-emerald-400">$0.00 (Zero Duty Loss)</span>
                </div>
                <div className="flex items-center justify-between text-slate-300 pb-1.5 border-b border-terminal-subtle">
                  <span className="text-slate-400">Incoterms 2020 Allocation:</span>
                  <span className="font-bold text-emerald-400">FOB Yantian (Non-Dutiable)</span>
                </div>
                <div className="flex items-center justify-between text-slate-300 pb-1.5 border-b border-terminal-subtle">
                  <span className="text-slate-400">Line Extension Math (500 × $45):</span>
                  <span className="font-bold text-emerald-400">$22,500.00 (Verified)</span>
                </div>
                <div className="flex items-center justify-between text-slate-300">
                  <span className="text-slate-400">HTS Classification Match:</span>
                  <span className="font-bold text-emerald-400">8542.31.0001 (Microcontrollers)</span>
                </div>
              </div>
            </div>
          ) : activeConceptId === "client_upload_audit" && auditData?.discrepancies.length === 0 ? (
            <div className="p-4 bg-slate-900/60 border border-slate-800 rounded-lg font-mono text-center space-y-2">
              <div className="text-xs font-bold text-slate-300">
                Zero Keyword Anomalies Detected by Browser Scanner
              </div>
              <div className="text-[11px] text-slate-400 max-w-sm mx-auto">
                No common pattern triggers (such as CIF without marine insurance or detention surcharges) were flagged in this file. This heuristic check does not constitute a formal statutory audit.
              </div>
            </div>
          ) : (
            auditData?.discrepancies.map((disc) => (
              <div key={disc.id} className="space-y-2">
                <DiscrepancyCard
                  key={disc.id}
                  discrepancy={disc}
                  isActive={activeDiscrepancyId === disc.id}
                  onHover={setActiveDiscrepancyId}
                  onClick={handleCardClick}
                  onFocusMobileDoc={() => {
                    setActiveDiscrepancyId(disc.id);
                    setMobileTab("doc");
                  }}
                />
                {(disc.confidence < 0.85 || disc.severity === "critical") && (
                  <div className="pl-2 border-l-2 border-amber-500/60">
                    <ThreeWayResolutionBar
                      discrepancyId={disc.id}
                      confidence={disc.confidence}
                      statutoryCode={disc.statutory_code}
                    />
                  </div>
                )}
              </div>
            ))
          )}
        </div>
      )}

      {/* Sub-Tab 2: CargoWise eAdaptor XML Viewer */}
      {rightTerminalTab === "cargowise" && (
        <div className="flex-1 overflow-y-auto p-4">
          <CargoWiseXmlViewer conceptId={activeConceptId} />
        </div>
      )}

      {/* Sub-Tab 3: Developer API Sandbox */}
      {rightTerminalTab === "developer_api" && (
        <div className="flex-1 overflow-y-auto p-4">
          <DeveloperApiSandbox />
        </div>
      )}
    </div>
  );
};
