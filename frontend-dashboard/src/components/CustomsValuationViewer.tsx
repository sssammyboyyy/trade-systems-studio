"use client";

import React, { useState, useEffect } from "react";
import { TabularAmount } from "./TabularAmount";
import { motion, AnimatePresence } from "framer-motion";
import {
  AssistItem,
  EntryValuationAudit,
  PriorDisclosurePackage,
  AmortizationMethod,
} from "@/lib/types";
import { fetchValuationAudit, generatePriorDisclosurePackage } from "@/lib/api";
import { soundEngine } from "@/lib/audio";
import { Printer } from "lucide-react";

interface CustomsValuationViewerProps {
  onLeadTrigger?: () => void;
}

export const CustomsValuationViewer: React.FC<CustomsValuationViewerProps> = ({
  onLeadTrigger,
}) => {
  const [audit, setAudit] = useState<EntryValuationAudit | null>(null);
  const [priorDisclosure, setPriorDisclosure] = useState<PriorDisclosurePackage | null>(null);
  const [showDisclosureModal, setShowDisclosureModal] = useState<boolean>(false);
  const [selectedAmortization, setSelectedAmortization] = useState<AmortizationMethod>("units_produced");
  const [copied, setCopied] = useState<boolean>(false);
  const [loading, setLoading] = useState<boolean>(true);

  useEffect(() => {
    let isMounted = true;
    setLoading(true);
    fetchValuationAudit()
      .then((res) => {
        if (isMounted) {
          setAudit(res);
          setLoading(false);
        }
      })
      .catch(() => {
        if (isMounted) setLoading(false);
      });

    generatePriorDisclosurePackage()
      .then((res) => {
        if (isMounted) setPriorDisclosure(res);
      })
      .catch(() => {});

    return () => {
      isMounted = false;
    };
  }, []);

  useEffect(() => {
    if (!showDisclosureModal) return;
    const handleKeyDown = (e: KeyboardEvent) => {
      if (e.key === "Escape") {
        setShowDisclosureModal(false);
      }
    };
    window.addEventListener("keydown", handleKeyDown);
    return () => window.removeEventListener("keydown", handleKeyDown);
  }, [showDisclosureModal]);

  const handleOpenDisclosure = () => {
    soundEngine.click();
    setShowDisclosureModal(true);
  };

  const handleCopyLetter = () => {
    if (priorDisclosure?.letter_text) {
      navigator.clipboard.writeText(priorDisclosure.letter_text);
      soundEngine.playSuccess();
      setCopied(true);
      setTimeout(() => setCopied(false), 2500);
    }
  };

  const handlePrintLetter = () => {
    soundEngine.click();
    const printWindow = window.open("", "_blank");
    if (!printWindow) return;
    const tenderFormatted = Number(audit?.prior_disclosure_tender_amount || 0).toLocaleString("en-US", {
      minimumFractionDigits: 2,
    });
    const printDoc = printWindow.document;
    printDoc.open();
    printDoc.write(`<!DOCTYPE html>
<html>
  <head>
    <title>19 CFR § 162.74 Formal Prior Disclosure</title>
    <style>
      body { font-family: 'Times New Roman', Times, serif; font-size: 11pt; line-height: 1.5; padding: 48px; color: #111; max-width: 800px; margin: 0 auto; }
      .header { text-align: center; font-weight: bold; margin-bottom: 24px; border-bottom: 2px solid #0F172A; padding-bottom: 12px; }
      .badge { font-size: 13pt; letter-spacing: 1px; }
      .sub { font-size: 9pt; font-weight: normal; margin-top: 4px; }
      .meta { font-family: monospace; font-size: 9pt; margin-bottom: 20px; color: #333; }
      pre { font-family: 'Times New Roman', Times, serif; white-space: pre-wrap; font-size: 10.5pt; line-height: 1.5; margin: 0; }
      .signature { margin-top: 40px; border-top: 1px solid #666; padding-top: 12px; font-size: 10pt; }
      @media print { body { padding: 20px; } }
    </style>
  </head>
  <body>
    <div class="header">
      <div class="badge">PRELIMINARY COMPLIANCE DRAFT -- FOR BROKER / COUNSEL REVIEW</div>
      <div class="sub">UNITED STATES CUSTOMS AND BORDER PROTECTION • FORMAL PRIOR DISCLOSURE</div>
    </div>
    <div id="meta-block" class="meta"></div>
    <pre id="letter-body"></pre>
    <div class="signature">
      <strong>Importer of Record / Authorized Agent Authorization</strong><br/>
      <span id="tender-statutory-line"></span>
    </div>
  </body>
</html>`);
    printDoc.close();

    const metaEl = printDoc.getElementById("meta-block");
    if (metaEl) {
      metaEl.textContent = `FILING REF: ${priorDisclosure?.filing_reference_id || "FILING"} | PORT: ${priorDisclosure?.port_of_entry || "PORT"}`;
    }
    const bodyEl = printDoc.getElementById("letter-body");
    if (bodyEl) {
      bodyEl.textContent = priorDisclosure?.letter_text || "";
    }
    const tenderEl = printDoc.getElementById("tender-statutory-line");
    if (tenderEl) {
      tenderEl.textContent = `Prior Disclosure Statutory Tender Computed: $${tenderFormatted} (19 U.S.C. § 1505 Lawful Duty Loss + Statutory Interest)`;
    }

    printWindow.onload = () => {
      printWindow.print();
    };
  };

  return (
    <div aria-busy={loading} className="flex-1 flex flex-col bg-canvas-dark text-ink-primary overflow-hidden">
      {/* Top Banner */}
      <div className="border-b border-terminal-subtle bg-terminal-slate/90 backdrop-blur px-6 py-4 flex flex-wrap items-center justify-between gap-4">
        <div>
          <div className="flex items-center gap-2">
            <span className="inline-block w-2.5 h-2.5 rounded-full bg-emerald-400 animate-pulse" />
            <h2 className="text-sm font-semibold tracking-wider uppercase text-emerald-400">
              Pillar 04: CBP Assist & Valuation Register
            </h2>
          </div>
          <p className="text-xs text-slate-400 mt-0.5">
            19 CFR § 152.103 Transaction Value Amortization & 19 CFR § 162.74 Prior Disclosure Penalty Barricade
          </p>
        </div>

        {/* Action Button */}
        <button
          onClick={handleOpenDisclosure}
          className="px-4 py-2 text-xs font-mono font-bold rounded bg-emerald-500 hover:bg-emerald-400 text-black transition-all shadow-md shadow-emerald-500/20 flex items-center gap-2"
        >
          <span>📜</span>
          <span>Generate 19 CFR § 162.74 Prior Disclosure Filing</span>
        </button>
      </div>

      {/* Metric Cards Banner */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-4 px-6 pt-5">
        <div className="p-4 rounded-lg bg-terminal-slate border border-red-500/40 relative overflow-hidden">
          <div className="text-[10px] font-mono uppercase tracking-wider text-red-400 font-semibold">
            19 U.S.C. § 1592 Gross Negligence Exposure (4.0x)
          </div>
          <div className="text-2xl font-bold font-mono text-red-400 mt-1">
            ${Number(audit?.gross_negligence_penalty_exposure || 0).toLocaleString("en-US", { minimumFractionDigits: 2 })}
          </div>
          <div className="text-[11px] text-slate-400 mt-1">
            Civil penalty assessed if CBP initiates formal audit before voluntary disclosure
          </div>
        </div>

        <div className="p-4 rounded-lg bg-terminal-slate border border-amber-500/40 relative overflow-hidden">
          <div className="text-[10px] font-mono uppercase tracking-wider text-amber-400 font-semibold">
            Prior Disclosure Tender Amount (19 CFR § 162.74)
          </div>
          <div className="text-2xl font-bold font-mono text-amber-300 mt-1">
            ${Number(audit?.prior_disclosure_tender_amount || 0).toLocaleString("en-US", { minimumFractionDigits: 2 })}
          </div>
          <div className="text-[11px] text-slate-400 mt-1">
            Actual duty underpayment (${Number(audit?.duty_underpayment || 0).toFixed(2)}) + 19 U.S.C. § 1505 interest (${Number(audit?.statutory_interest_19usc1505 || 0).toFixed(2)})
          </div>
        </div>

        <div className="p-4 rounded-lg bg-terminal-slate border border-emerald-500/50 bg-emerald-950/10 relative overflow-hidden">
          <div className="text-[10px] font-mono uppercase tracking-wider text-emerald-400 font-semibold">
            Net Civil Liability Barricaded / Avoided
          </div>
          <div className="text-2xl font-bold font-mono text-emerald-400 mt-1">
            ${Number(audit?.total_liability_avoided || 0).toLocaleString("en-US", { minimumFractionDigits: 2 })}
          </div>
          <div className="text-[11px] text-slate-400 mt-1">
            Statutory penalty protection attained upon tender of voluntary disclosure package
          </div>
        </div>
      </div>

      {/* Main Content Area */}
      <div className="flex-1 overflow-y-auto p-6 grid grid-cols-1 lg:grid-cols-12 gap-6">
        {/* Left Column: GAAP Assist Register & Deductions */}
        <div className="lg:col-span-8 space-y-6">
          {/* Assist Register Table */}
          <div className="p-5 rounded-lg border border-terminal-subtle bg-terminal-slate space-y-4">
            <div className="flex flex-wrap items-center justify-between gap-3">
              <div>
                <h3 className="text-sm font-bold text-ink-primary uppercase tracking-wider">
                  Active Assist Register (19 U.S.C. § 1401a(h))
                </h3>
                <p className="text-xs text-slate-400 mt-0.5">
                  Track buyer-supplied tools, dies, molds, and overseas engineering design amortizations
                </p>
              </div>

              {/* Amortization Method Switcher */}
              <div className="flex items-center gap-1 bg-canvas-dark p-1 rounded border border-terminal-subtle text-xs font-mono">
                <button
                  onClick={() => {
                    soundEngine.click();
                    setSelectedAmortization("units_produced");
                  }}
                  className={`px-2.5 py-1 rounded transition-all ${
                    selectedAmortization === "units_produced"
                      ? "bg-emerald-500/20 text-emerald-300 font-bold"
                      : "text-slate-400 hover:text-ink-primary"
                  }`}
                >
                  Units Produced (GAAP)
                </button>
                <button
                  onClick={() => {
                    soundEngine.click();
                    setSelectedAmortization("first_entry");
                  }}
                  className={`px-2.5 py-1 rounded transition-all ${
                    selectedAmortization === "first_entry"
                      ? "bg-emerald-500/20 text-emerald-300 font-bold"
                      : "text-slate-400 hover:text-ink-primary"
                  }`}
                >
                  First Entry Method
                </button>
              </div>
            </div>

            {/* Table */}
            <div className="overflow-x-auto">
              <table className="w-full min-w-[720px] text-left text-xs font-mono">
                <thead className="bg-canvas-dark text-slate-400 uppercase text-[10px] tracking-wider border-b border-terminal-subtle">
                  <tr>
                    <th className="py-2.5 px-3">Assist ID / Description</th>
                    <th className="py-2.5 px-3">Category</th>
                    <th className="py-2.5 px-3 text-right">Acquisition Cost</th>
                    <th className="py-2.5 px-3 text-right">Amortized / Unit</th>
                    <th className="py-2.5 px-3 text-right">Unamortized Bal.</th>
                    <th className="py-2.5 px-3 text-center">CBP Status</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-terminal-subtle">
                  {audit?.assists_audited.map((item: AssistItem) => (
                    <tr key={item.id} className="hover:bg-slate-800/20 transition-colors">
                      <td className="py-3 px-3">
                        <div className="font-bold text-ink-primary">{item.id}</div>
                        <div className="text-[11px] text-slate-400 font-sans mt-0.5">
                          {item.description}
                        </div>
                        <div className="text-[10px] text-slate-400 mt-0.5">
                          Supplier: {item.supplier_name} ({item.country_of_origin})
                        </div>
                      </td>
                      <td className="py-3 px-3">
                        <span className="px-2 py-0.5 text-[10px] rounded bg-slate-800 text-slate-300 border border-slate-700 uppercase">
                          {item.category.replace(/_/g, " ")}
                        </span>
                      </td>
                      <td className="py-3 px-3 text-right text-ink-primary font-semibold">
                        ${Number(item.total_acquisition_cost).toLocaleString("en-US", { minimumFractionDigits: 2 })}
                      </td>
                      <td className="py-3 px-3 text-right text-cyan-400 font-semibold">
                        ${Number(item.per_unit_amortized_cost).toFixed(2)}
                      </td>
                      <td className="py-3 px-3 text-right text-slate-300">
                        ${Number(item.remaining_unamortized_cost).toLocaleString("en-US", { minimumFractionDigits: 2 })}
                      </td>
                      <td className="py-3 px-3 text-center">
                        {item.is_declared_to_cbp ? (
                          <span className="px-2 py-0.5 text-[10px] rounded bg-emerald-500/10 text-emerald-400 border border-emerald-500/30">
                            DECLARED
                          </span>
                        ) : (
                          <span className="px-2 py-0.5 text-[10px] rounded bg-red-500/10 text-red-400 border border-red-500/30 animate-pulse font-bold">
                            ⚠️ OMITTED
                          </span>
                        )}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>

          {/* CIF / FOB Non-Dutiable Freight Deductions Reconciler */}
          <div className="p-5 rounded-lg border border-terminal-subtle bg-terminal-slate space-y-3">
            <div className="flex items-center justify-between border-b border-terminal-subtle pb-3">
              <div>
                <h4 className="text-xs font-bold text-ink-primary uppercase tracking-wider">
                  CIF Freight & Marine Insurance Statutory Deductions (19 CFR § 152.103 Ex. 4)
                </h4>
                <div className="text-[11px] text-slate-400 mt-0.5">
                  International freight and marine insurance are legally non-dutiable and must be deducted from CIF invoices
                </div>
              </div>
              <span className="px-2 py-0.5 text-[10px] font-mono bg-cyan-500/10 text-cyan-400 border border-cyan-500/30 rounded">
                Deduction Active
              </span>
            </div>

            <div className="grid grid-cols-1 md:grid-cols-3 gap-3 pt-1 text-xs font-mono">
              <div className="p-3 rounded bg-canvas-dark border border-terminal-subtle">
                <div className="text-[10px] text-slate-500 uppercase">Invoiced Incoterm</div>
                <div className="text-sm font-bold text-ink-primary mt-1">{audit?.invoice_incoterm}</div>
              </div>
              <div className="p-3 rounded bg-canvas-dark border border-terminal-subtle">
                <div className="text-[10px] text-slate-500 uppercase">Ocean Freight Deducted</div>
                <div className="text-sm font-bold text-cyan-400 mt-1">
                  -${Number(audit?.international_freight_in_invoice || 0).toLocaleString("en-US", { minimumFractionDigits: 2 })}
                </div>
              </div>
              <div className="p-3 rounded bg-canvas-dark border border-terminal-subtle">
                <div className="text-[10px] text-slate-500 uppercase">Marine Insurance Deducted</div>
                <div className="text-sm font-bold text-cyan-400 mt-1">
                  -${Number(audit?.marine_insurance_in_invoice || 0).toLocaleString("en-US", { minimumFractionDigits: 2 })}
                </div>
              </div>
            </div>
          </div>
        </div>

        {/* Right Column: Statutory Reconciliation & Prior Disclosure Action */}
        <div className="lg:col-span-4 space-y-6">
          <div className="p-5 rounded-lg border border-terminal-subtle bg-terminal-slate space-y-4">
            <div className="border-b border-terminal-subtle pb-3">
              <h4 className="type-mono-data font-medium uppercase text-ink-primary">
                Statutory Valuation Reconciliation
              </h4>
              <div className="type-caption-mono text-ink-muted">
                100% Python Decimal Deterministic Math
              </div>
            </div>

            <div className="space-y-2.5 type-mono-data">
              <div className="flex justify-between items-center text-ink-muted">
                <span>Declared Transaction Value:</span>
                <TabularAmount value={Number(audit?.declared_transaction_value || 0)} className="text-ink-numeric" />
              </div>

              <div className="flex justify-between items-center text-cyan-400">
                <span>Less: CIF Freight/Insurance:</span>
                <TabularAmount value={-Math.abs(Number(audit?.improper_cif_overvaluation || 0))} className="text-cyan-400" />
              </div>

              <div className="flex justify-between items-center text-ink-crimson font-medium">
                <span>Plus: Omitted Assists:</span>
                <TabularAmount value={Math.abs(Number(audit?.assists_omitted_cost || 0))} showPlusSign className="text-ink-crimson" />
              </div>

              <div className="pt-2 border-t border-terminal-subtle flex justify-between items-center font-medium">
                <span className="text-ink-primary">Adjusted Lawful Value:</span>
                <TabularAmount value={Number(audit?.adjusted_lawful_dutiable_value || 0)} className="text-ink-primary text-sm font-semibold" />
              </div>

              <div className="flex justify-between items-center text-ink-muted">
                <span>Duty Rate (Ad Valorem):</span>
                <span className="tabular-nums">{(Number(audit?.duty_rate_ad_valorem || 0) * 100).toFixed(2)}%</span>
              </div>

              <div className="flex justify-between items-center text-ink-muted">
                <span>Lawful Customs Duty Due:</span>
                <TabularAmount value={Number(audit?.lawful_duty_due || 0)} className="text-ink-secondary" />
              </div>

              <div className="flex justify-between items-center text-slate-400">
                <span>Declared Duty Tendered:</span>
                <span className="text-slate-200">${Number(audit?.declared_duty_paid || 0).toLocaleString("en-US", { minimumFractionDigits: 2 })}</span>
              </div>

              <div className="pt-2 border-t border-terminal-subtle flex justify-between items-center font-bold text-red-400">
                <span>Actual Duty Loss:</span>
                <span className="text-sm">${Number(audit?.duty_underpayment || 0).toLocaleString("en-US", { minimumFractionDigits: 2 })}</span>
              </div>

              <div className="flex justify-between items-center text-amber-300">
                <span>19 U.S.C. § 1505 Interest (7%):</span>
                <span>${Number(audit?.statutory_interest_19usc1505 || 0).toLocaleString("en-US", { minimumFractionDigits: 2 })}</span>
              </div>

              <div className="p-3 rounded bg-canvas-dark border border-amber-500/40 flex justify-between items-center font-bold">
                <span className="text-xs uppercase tracking-wider text-amber-300">Prior Disclosure Tender:</span>
                <span className="text-base text-amber-400">${Number(audit?.prior_disclosure_tender_amount || 0).toLocaleString("en-US", { minimumFractionDigits: 2 })}</span>
              </div>
            </div>

            <button
              onClick={handleOpenDisclosure}
              className="w-full py-2.5 px-3 rounded bg-emerald-500 hover:bg-emerald-400 text-black font-bold text-xs uppercase tracking-wider transition-all shadow-md shadow-emerald-500/20"
            >
              Review & Export Prior Disclosure Letter
            </button>
          </div>
        </div>
      </div>

      {/* Prior Disclosure Modal */}
      <AnimatePresence>
        {showDisclosureModal && (
          <div
            role="dialog"
            aria-modal="true"
            aria-labelledby="prior-disclosure-modal-title"
            className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-canvas-dark/80 backdrop-blur-sm"
          >
            <motion.div
              initial={{ opacity: 0, scale: 0.95 }}
              animate={{ opacity: 1, scale: 1 }}
              exit={{ opacity: 0, scale: 0.95 }}
              className="w-full max-w-3xl bg-terminal-slate border border-terminal-subtle rounded-xl shadow-2xl flex flex-col max-h-[90vh] overflow-hidden"
            >
              <div className="p-5 border-b border-terminal-subtle flex items-center justify-between">
                <div>
                  <h3 id="prior-disclosure-modal-title" className="text-base font-bold text-ink-primary flex items-center gap-2">
                    <span>📜</span>
                    <span>19 CFR § 162.74 Formal Prior Disclosure Filing</span>
                  </h3>
                  <div className="text-xs text-slate-400 font-mono mt-0.5">
                    Ref ID: {priorDisclosure?.filing_reference_id} | Addressed to: {priorDisclosure?.port_of_entry}
                  </div>
                </div>
                <button
                  onClick={() => setShowDisclosureModal(false)}
                  aria-label="Close Prior Disclosure dialog"
                  className="text-slate-400 hover:text-ink-primary text-lg p-1 rounded focus:outline-none focus:ring-2 focus:ring-emerald-400"
                >
                  ✕
                </button>
              </div>

              {/* Letter Preview Box */}
              <div className="flex-1 overflow-y-auto p-5 bg-canvas-dark font-mono text-xs text-slate-300 leading-relaxed whitespace-pre-wrap select-all">
                {priorDisclosure?.letter_text}
              </div>

              {/* Modal Footer */}
              <div className="p-4 border-t border-terminal-subtle bg-terminal-slate flex items-center justify-between">
                <div className="text-xs font-mono text-emerald-400 flex items-center gap-1.5">
                  <span>✓</span>
                  <span>Mitigates 19 U.S.C. § 1592 penalties from up to 4.0x down to $0 penalty</span>
                </div>
                <div className="flex items-center gap-2 sm:gap-3">
                  <button
                    onClick={handleCopyLetter}
                    className="px-3 sm:px-4 py-2 rounded border border-terminal-subtle bg-terminal-slate text-xs font-mono font-medium hover:border-slate-500 text-ink-primary transition-all flex items-center gap-1.5"
                  >
                    <span>{copied ? "✓ Copied!" : "📋 Copy"}</span>
                  </button>
                  <button
                    onClick={handlePrintLetter}
                    className="px-3 sm:px-4 py-2 rounded border border-emerald-500/50 bg-emerald-950/30 text-xs font-mono font-medium hover:bg-emerald-950/60 text-emerald-300 transition-all flex items-center gap-1.5"
                    title="Print or Save as Official PDF Letterhead"
                  >
                    <Printer className="w-3.5 h-3.5 text-emerald-400" />
                    <span>Print / PDF</span>
                  </button>
                  <button
                    onClick={() => {
                      soundEngine.click();
                      setShowDisclosureModal(false);
                      onLeadTrigger?.();
                    }}
                    className="px-4 py-2 rounded bg-emerald-500 hover:bg-emerald-400 text-black text-xs font-bold uppercase tracking-wider transition-all"
                  >
                    Export Legal Review Brief
                  </button>
                </div>
              </div>
            </motion.div>
          </div>
        )}
      </AnimatePresence>
    </div>
  );
};
