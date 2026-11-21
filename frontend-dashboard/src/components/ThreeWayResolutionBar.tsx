"use client";

import React, { useState } from "react";
import { CheckCircle2, FileQuestion, ShieldAlert, RotateCcw, AlertTriangle } from "lucide-react";
import { usePreIngestFirewall, playPseudoHaptic } from "@/lib/firewall-core";
import { ResolutionActionType } from "@/lib/types";

interface ThreeWayResolutionBarProps {
  discrepancyId: string;
  confidence: number;
  statutoryCode: string;
  onResolved?: (action: ResolutionActionType) => void;
}

const REASON_CODES: Record<ResolutionActionType, string[]> = {
  approve_clean: [
    "CONFIRMED_SHIPPERS_CORRECTED_INVOICE",
    "VERIFIED_STATUTORY_TARIFF_EXCLUSION",
    "CIF_FREIGHT_INSURANCE_ITEMISED_ON_ENTRY",
    "DE_MINIMIS_STATUTORY_TOLERANCE_SATISFIED",
  ],
  request_paperwork: [
    "MISSING_CARRIER_ORIGINAL_OCEAN_BL",
    "UNPROVIDED_TOOLING_ASSIST_PURCHASE_ORDER",
    "MISSING_INSURANCE_CERTIFICATE",
    "DISCORDANT_CHASSIS_SPLIT_WORK_ORDER",
  ],
  escalate_broker: [
    "POTENTIAL_19_USC_1592_EXPOSURE_CULPABILITY_REVIEW",
    "OFAC_50_PERCENT_BENEFICIAL_OWNERSHIP_REVIEW",
    "CONTESTED_WCO_GRI_ESSENTIAL_CHARACTER_DISPUTE",
    "PRIOR_DISCLOSURE_PETITION_REQUIRED_19_CFR_162_74",
  ],
};

export const ThreeWayResolutionBar: React.FC<ThreeWayResolutionBarProps> = ({
  discrepancyId,
  confidence,
  statutoryCode,
  onResolved,
}) => {
  const { resolutionHistory, applyResolution, undoResolution, ledgerStorage } = usePreIngestFirewall();
  const existingResolution = resolutionHistory[discrepancyId];

  const [activeAction, setActiveAction] = useState<ResolutionActionType | null>(null);
  const [selectedReason, setSelectedReason] = useState<string>("");

  const handleActionSelect = (action: ResolutionActionType) => {
    playPseudoHaptic();
    setActiveAction(action);
    setSelectedReason(REASON_CODES[action][0]);
  };

  const handleConfirm = () => {
    if (!activeAction || !selectedReason) return;
    playPseudoHaptic();
    applyResolution(discrepancyId, activeAction, selectedReason);
    if (onResolved) onResolved(activeAction);
    setActiveAction(null);
  };

  const handleCancel = () => {
    playPseudoHaptic();
    setActiveAction(null);
  };

  if (existingResolution) {
    const actionLabel =
      existingResolution.action === "approve_clean"
        ? "APPROVED"
        : existingResolution.action === "request_paperwork"
        ? "DOCUMENTS REQUESTED"
        : "ESCALATED TO BROKER / COUNSEL";

    const badgeColor =
      existingResolution.action === "approve_clean"
        ? "bg-emerald-500/10 border-emerald-500/30 text-emerald-400"
        : existingResolution.action === "request_paperwork"
        ? "bg-amber-500/10 border-amber-500/30 text-amber-400"
        : "bg-red-500/10 border-red-500/30 text-red-400";

    return (
      <div className="mt-3 p-2.5 rounded-lg border border-terminal-subtle bg-terminal-slate flex items-center justify-between gap-2 text-xs font-mono">
        <div className="flex min-w-0 items-center gap-2">
          <span className={`shrink-0 px-2 py-0.5 rounded text-[10px] font-bold border ${badgeColor}`}>
            {actionLabel}
          </span>
          <span className="text-ink-muted text-[11px] truncate" title={existingResolution.reason_code}>
            {existingResolution.reason_code} · {ledgerStorage === "server" ? "logged to server ledger" : "saved in this browser"}
          </span>
        </div>
        <button
          onClick={() => {
            playPseudoHaptic();
            undoResolution(discrepancyId);
          }}
          className="flex items-center gap-1 text-[11px] text-slate-400 hover:text-slate-200 transition-colors p-1"
          title="Reopen (recorded as a new ledger entry)"
        >
          <RotateCcw className="w-3 h-3" />
          <span>Reopen</span>
        </button>
      </div>
    );
  }

  return (
    <div className="mt-3 p-3 rounded-lg border border-terminal-subtle bg-canvas-dark/90">
      <div className="flex items-center justify-between gap-2 mb-2">
        <div className="flex min-w-0 items-center gap-1.5 text-[11px] font-mono text-ink-amber">
          <AlertTriangle className="w-3.5 h-3.5 shrink-0" />
          <span className="truncate">
            Review · confidence {(confidence * 100).toFixed(0)}% · {statutoryCode}
          </span>
        </div>
      </div>

      {!activeAction ? (
        <div className="grid grid-cols-3 gap-2">
          <button
            onClick={() => handleActionSelect("approve_clean")}
            className="flex items-center justify-center gap-1.5 py-1.5 px-2 rounded-md bg-emerald-500/10 hover:bg-emerald-500/20 border border-emerald-500/30 text-emerald-300 text-xs font-mono transition-all active:scale-[0.98]"
          >
            <CheckCircle2 className="w-3.5 h-3.5" />
            <span>Approve</span>
          </button>

          <button
            onClick={() => handleActionSelect("request_paperwork")}
            className="flex items-center justify-center gap-1.5 py-1.5 px-2 rounded-md bg-amber-500/10 hover:bg-amber-500/20 border border-amber-500/30 text-amber-300 text-xs font-mono transition-all active:scale-[0.98]"
          >
            <FileQuestion className="w-3.5 h-3.5" />
            <span>Request Docs</span>
          </button>

          <button
            onClick={() => handleActionSelect("escalate_broker")}
            className="flex items-center justify-center gap-1.5 py-1.5 px-2 rounded-md bg-red-500/10 hover:bg-red-500/20 border border-red-500/30 text-red-300 text-xs font-mono transition-all active:scale-[0.98]"
          >
            <ShieldAlert className="w-3.5 h-3.5" />
            <span>Escalate</span>
          </button>
        </div>
      ) : (
        <div className="space-y-2 pt-1 border-t border-terminal-subtle">
          <div className="flex items-center justify-between">
            <span className="text-[11px] font-mono text-ink-secondary">
              Reason
            </span>
            <button
              onClick={handleCancel}
              className="text-[10px] font-mono text-slate-400 hover:text-slate-200"
            >
              Cancel
            </button>
          </div>

          <select
            aria-label="Statutory Reason Code"
            value={selectedReason}
            onChange={(e) => setSelectedReason(e.target.value)}
            className="w-full text-xs font-mono bg-terminal-slate border border-terminal-subtle rounded p-1.5 text-ink-primary focus:outline-none focus:border-cobalt-500"
          >
            {REASON_CODES[activeAction].map((code) => (
              <option key={code} value={code}>
                {code.toLowerCase().replace(/_/g, " ")}
              </option>
            ))}
          </select>

          <button
            onClick={handleConfirm}
            className="w-full py-1.5 rounded bg-blue-600 hover:bg-blue-500 text-canvas-stone font-mono text-xs font-semibold tracking-wide transition-all active:scale-[0.98]"
          >
            Record decision
          </button>
        </div>
      )}
    </div>
  );
};
