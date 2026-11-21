"use client";

import React, { useEffect, useRef } from "react";
import { X, Printer, ShieldCheck } from "lucide-react";
import { AuditResult } from "@/lib/types";
import { sound } from "@/lib/audio";
import { formatUsd, sumMoneyStrings } from "@/lib/money";

interface ExecutiveDossierModalProps {
  isOpen: boolean;
  onClose: () => void;
  auditData: AuditResult | null;
}

export const ExecutiveDossierModal: React.FC<ExecutiveDossierModalProps> = ({
  isOpen,
  onClose,
  auditData,
}) => {
  const modalRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (!isOpen) return;
    const handleKeyDown = (e: KeyboardEvent) => {
      if (e.key === "Escape") {
        onClose();
      }
    };
    window.addEventListener("keydown", handleKeyDown);
    return () => window.removeEventListener("keydown", handleKeyDown);
  }, [isOpen, onClose]);

  useEffect(() => {
    if (!isOpen) return;
    const focusableElements = modalRef.current?.querySelectorAll<HTMLElement>(
      'button, [href], input, select, textarea, [tabindex]:not([tabindex="-1"])'
    );
    if (focusableElements && focusableElements.length > 0) {
      focusableElements[0].focus();
    }
    const handleTabTrap = (e: KeyboardEvent) => {
      if (e.key !== "Tab" || !focusableElements || focusableElements.length === 0) return;
      const firstEl = focusableElements[0];
      const lastEl = focusableElements[focusableElements.length - 1];
      if (e.shiftKey && document.activeElement === firstEl) {
        e.preventDefault();
        lastEl.focus();
      } else if (!e.shiftKey && document.activeElement === lastEl) {
        e.preventDefault();
        firstEl.focus();
      }
    };
    window.addEventListener("keydown", handleTabTrap);
    return () => window.removeEventListener("keydown", handleTabTrap);
  }, [isOpen]);

  if (!isOpen || !auditData) return null;

  const handlePrint = () => {
    sound.playLock();
    window.print();
  };

  return (
    <div
      role="dialog"
      aria-modal="true"
      aria-labelledby="executive-dossier-modal-title"
      className="fixed inset-0 z-50 flex items-center justify-center p-3 sm:p-6 bg-slate-950/70 dark:bg-canvas-dark/85 backdrop-blur-md animate-in fade-in duration-200 overflow-y-auto"
    >
      <div
        ref={modalRef}
        className="relative w-full max-w-3xl bg-white text-slate-900 border border-slate-300 p-6 sm:p-10 shadow-2xl rounded-sm my-auto font-sans"
      >
        {/* Top Control Bar */}
        <div className="flex items-center justify-between pb-4 mb-6 border-b border-slate-200 print:hidden">
          <div className="flex items-center gap-2">
            <span className="text-[10px] font-mono uppercase px-2 py-0.5 bg-cobalt-100 text-cobalt-800 font-bold rounded-xs">
              Executive Briefing Paper
            </span>
            <span className="text-xs text-slate-600 font-mono">
              CONFIDENTIAL TECHNICAL WORK PRODUCT • PREPARED FOR LICENSED BROKER OR COUNSEL REVIEW
            </span>
          </div>
          <div className="flex items-center gap-2">
            <button
              onClick={handlePrint}
              aria-label="Print or save as PDF"
              className="flex items-center gap-1.5 px-3 py-1.5 bg-slate-900 hover:bg-slate-800 text-canvas-stone text-xs font-mono font-bold uppercase rounded-sm transition-all cursor-pointer"
            >
              <Printer className="w-3.5 h-3.5" />
              <span>Print / Save PDF</span>
            </button>
            <button
              onClick={onClose}
              aria-label="Close dialog"
              className="p-1.5 text-slate-400 hover:text-slate-700 transition-colors cursor-pointer"
            >
              <X className="w-5 h-5" />
            </button>
          </div>
        </div>

        {/* Printable Letterhead */}
        <div className="flex items-start justify-between pb-6 mb-6 border-b-2 border-slate-900">
          <div>
            <div id="executive-dossier-modal-title" className="text-xl font-black uppercase tracking-wider text-slate-900 font-mono">
              SAMUEL • TRADETECH SYSTEMS STUDIO
            </div>
            <div className="text-xs text-slate-600 font-mono mt-0.5">
              Autonomous Trade Intelligence & Customs Defense Systems
            </div>
            <div className="text-[11px] text-slate-600 font-mono mt-1">
              Engaged Practice: Principal AI Systems Architecture & Tariff Mitigation
            </div>
          </div>
          <div className="text-right font-mono text-[11px] text-slate-600">
            <div>DATE: {new Date().toLocaleDateString("en-US", { dateStyle: "long" })}</div>
            <div>STATUS: VERIFIED PRE-PAYMENT DEFECT</div>
            <div>DOC REF: {auditData.document_filename}</div>
          </div>
        </div>

        {/* Executive Summary */}
        <div className="mb-6">
          <h3 className="text-sm font-bold uppercase tracking-wider text-slate-900 font-mono mb-2">
            1. Executive Audit Finding & Capital Defense Brief
          </h3>
          <p className="text-xs text-slate-700 leading-relaxed">
            TradeTech Systems Studio executed an automated deterministic audit of{" "}
            <strong>{auditData.document_filename}</strong> using localized coordinate tokenization and Python Decimal precision arithmetic. The system identified{" "}
            <strong>{auditData.discrepancies.length} material compliance defects</strong> representing a statutory financial exposure of{" "}
            <span className="font-bold text-red-600">
              {formatUsd(
                sumMoneyStrings(
                  ...auditData.discrepancies.map((d) => d.exposure_amount)
                )
              )}
            </span>.
          </p>
        </div>

        {/* Findings Ledger */}
        <div className="mb-6">
          <h3 className="text-sm font-bold uppercase tracking-wider text-slate-900 font-mono mb-2">
            2. Verified Statutory Discrepancy Ledger
          </h3>
          <table className="w-full border border-slate-300 text-xs text-left border-collapse">
            <thead className="bg-slate-100 font-mono text-[10px] text-slate-700 uppercase">
              <tr className="border-b border-slate-300">
                <th className="p-2 border-r border-slate-300">Citation</th>
                <th className="p-2 border-r border-slate-300">Defect Description</th>
                <th className="p-2 border-r border-slate-300 text-right">Exposure</th>
                <th className="p-2">Confidence</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-200">
              {auditData.discrepancies.map((disc) => (
                <tr key={disc.id} className="text-[11px]">
                  <td className="p-2 font-mono font-bold text-slate-900 border-r border-slate-300">
                    {disc.statutory_code}
                  </td>
                  <td className="p-2 border-r border-slate-300">
                    <div className="font-semibold text-slate-800">{disc.title}</div>
                    <div className="text-[10px] text-slate-600 mt-0.5">{disc.description}</div>
                  </td>
                  <td className="p-2 font-mono font-bold text-red-600 border-r border-slate-300 text-right">
                    {formatUsd(disc.exposure_amount)}
                  </td>
                  <td className="p-2 font-mono text-slate-600">
                    {(disc.confidence * 100).toFixed(0)}% (pypdf/docling)
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>

        {/* Samuel's Recommended Architectural Remediation */}
        <div className="p-4 bg-slate-50 border border-slate-300 rounded-xs mb-6">
          <h4 className="text-xs font-bold uppercase tracking-wider text-slate-900 font-mono mb-1.5 flex items-center gap-1.5">
            <ShieldCheck className="w-4 h-4 text-cobalt-600" />
            <span>3. Samuel&apos;s Mandatory Remediation Protocol</span>
          </h4>
          <ol className="list-decimal list-inside text-xs text-slate-700 space-y-1 leading-relaxed">
            <li>
              <strong>Immediate Payment Interception:</strong> Dispute the unsupported lines with the carrier within the period on the invoice (46 CFR 541.8) before paying them.
            </li>
            <li>
              <strong>Prior Disclosure:</strong> A valid prior disclosure under 19 CFR § 162.74 limits a negligence or gross-negligence penalty to interest on the loss of duty (fraud: up to 100% of the loss); the loss itself must be tendered.
            </li>
            <li>
              <strong>Automated Gateway Deployment:</strong> Install Samuel&apos;s deterministic pre-payment audit engine to inspect all inbound 7501 summaries and carrier EDI 210 invoices.
            </li>
          </ol>
        </div>

        {/* Footer Signature */}
        <div className="pt-4 border-t border-slate-200 flex items-center justify-between font-mono text-[10px] text-slate-600">
          <div>
            <div>ANALYSIS BY: Samuel</div>
            <div>Principal AI Systems Architect & Trade Compliance Lead</div>
          </div>
          <div className="text-right">
            <div>TradeTech Systems Studio</div>
            <div>Autonomous Intelligence & Compliance Monorepo</div>
          </div>
        </div>
      </div>
    </div>
  );
};
