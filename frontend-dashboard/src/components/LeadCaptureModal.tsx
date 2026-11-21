"use client";

import React, { useState, useEffect, useRef } from "react";
import { submitLeadCapture, recordTelemetry } from "@/lib/supabase";
import { submitLeadApi } from "@/lib/api";
import { X, CheckCircle2, Shield, ArrowRight, Loader2, AlertCircle, Mail, Linkedin } from "lucide-react";

interface LeadCaptureModalProps {
  isOpen: boolean;
  onClose: () => void;
  activeConceptId: string;
}

export const LeadCaptureModal: React.FC<LeadCaptureModalProps> = ({
  isOpen,
  onClose,
  activeConceptId,
}) => {
  const [name, setName] = useState("");
  const [email, setEmail] = useState("");
  const [companyName, setCompanyName] = useState("");
  const [phone, setPhone] = useState("");
  const [volume, setVolume] = useState("500-2500 documents/mo");
  const [privacyConsent, setPrivacyConsent] = useState(false);
  const [showPrivacyNotice, setShowPrivacyNotice] = useState(false);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [isSubmitted, setIsSubmitted] = useState(false);
  const [submitError, setSubmitError] = useState<string | null>(null);
  const [leadId, setLeadId] = useState("");

  const modalRef = useRef<HTMLDivElement>(null);

  // Escape key listener & focus trapping
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
  }, [isOpen, isSubmitted, submitError]);

  if (!isOpen) return null;

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!email || !companyName || !privacyConsent) return;

    setIsSubmitting(true);
    setSubmitError(null);

    recordTelemetry({
      event_type: "lead_submitted",
      concept_id: activeConceptId,
      metadata: { volume_tier: volume },
    });

    const payload = {
      email,
      company_name: companyName,
      phone,
      monthly_import_volume: `${volume}${name ? ` [${name}]` : ""}`.slice(0, 50),
      source: "technical_architecture_review_modal",
      privacy_consent: privacyConsent,
    };

    // Try backend API endpoint first
    let result = await submitLeadApi(payload);

    // Fall back to Supabase if backend was unreachable
    if (!result.success) {
      result = await submitLeadCapture(payload);
    }

    setIsSubmitting(false);

    if (result.success && result.id) {
      setIsSubmitted(true);
      setLeadId(result.id);
    } else {
      setSubmitError(
        "The automated scheduling service is currently unreachable. Please contact Samuel directly via email or LinkedIn below."
      );
    }
  };

  return (
    <div
      role="dialog"
      aria-modal="true"
      aria-labelledby="lead-capture-modal-title"
      className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-slate-950/60 dark:bg-canvas-dark/85 backdrop-blur-sm animate-in fade-in duration-200"
    >
      <div
        ref={modalRef}
        className="relative w-full max-w-lg bg-white dark:bg-terminal-slate border border-slate-200 dark:border-terminal-subtle p-6 sm:p-7 shadow-2xl rounded-sm"
      >
        {/* Close Button */}
        <button
          onClick={onClose}
          aria-label="Close dialog"
          className="absolute top-4 right-4 p-1.5 text-slate-400 hover:text-slate-900 dark:text-slate-400 dark:hover:text-ink-primary transition-colors border border-slate-200 dark:border-terminal-subtle hover:bg-slate-100 dark:hover:bg-terminal-elevated rounded-sm"
        >
          <X className="w-4 h-4" />
        </button>

        {!isSubmitted ? (
          <div>
            <div className="flex items-center gap-2 mb-2">
              <span className="text-[10px] font-mono uppercase px-2 py-0.5 bg-cobalt-50 dark:bg-cobalt-950/80 border border-cobalt-200 dark:border-cobalt-800 text-cobalt-700 dark:text-cobalt-400 font-semibold rounded-xs">
                Technical Architecture Review
              </span>
              <span className="text-[10px] font-mono text-slate-400 dark:text-slate-400">
                Samuel | TradeTech Systems Studio
              </span>
            </div>

            <h3 id="lead-capture-modal-title" className="text-xl font-bold text-slate-900 dark:text-slate-100 mb-1">
              Schedule a Technical Architecture Review
            </h3>
            <p className="text-xs text-slate-600 dark:text-slate-400 leading-relaxed mb-5">
              A working session on the audit engine, provenance model, and integration surface, led by the engineer who built it.
            </p>

            {submitError && (
              <div className="mb-4 p-3.5 bg-amber-950/40 border border-amber-600/70 rounded-sm font-mono text-xs text-amber-200 space-y-2.5">
                <div className="flex items-start gap-2">
                  <AlertCircle className="w-4 h-4 text-amber-400 shrink-0 mt-0.5" />
                  <div className="leading-snug">{submitError}</div>
                </div>
                <div className="flex flex-wrap items-center gap-2 pt-1 border-t border-amber-800/60">
                  <a
                    href="mailto:samuel-tradetech@outlook.com?subject=Technical%20Architecture%20Review%20Request"
                    className="inline-flex items-center gap-1.5 px-2.5 py-1 bg-amber-900/60 hover:bg-amber-800/70 text-amber-100 border border-amber-600/60 rounded-xs text-[11px] font-semibold transition-colors"
                  >
                    <Mail className="w-3.5 h-3.5" />
                    <span>samuel-tradetech@outlook.com</span>
                  </a>
                  <a
                    href="https://www.linkedin.com/in/samuel-rencken-880410249"
                    target="_blank"
                    rel="noopener noreferrer"
                    className="inline-flex items-center gap-1.5 px-2.5 py-1 bg-blue-900/60 hover:bg-blue-800/70 text-blue-100 border border-blue-600/60 rounded-xs text-[11px] font-semibold transition-colors"
                  >
                    <Linkedin className="w-3.5 h-3.5" />
                    <span>Connect on LinkedIn</span>
                  </a>
                </div>
              </div>
            )}

            <form onSubmit={handleSubmit} className="space-y-4">
              <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
                <div>
                  <label className="block text-xs font-mono font-medium text-slate-700 dark:text-slate-300 mb-1">
                    Your Name *
                  </label>
                  <input
                    type="text"
                    required
                    value={name}
                    onChange={(e) => setName(e.target.value)}
                    placeholder="Jane Doe, VP Supply Chain"
                    className="w-full bg-slate-50 dark:bg-canvas-dark border border-slate-300 dark:border-terminal-subtle px-3 py-2 text-xs text-slate-900 dark:text-slate-100 focus:outline-none focus:border-cobalt-600 dark:focus:border-cobalt-400 font-mono rounded-sm"
                  />
                </div>

                <div>
                  <label className="block text-xs font-mono font-medium text-slate-700 dark:text-slate-300 mb-1">
                    Work Email *
                  </label>
                  <input
                    type="email"
                    required
                    value={email}
                    onChange={(e) => setEmail(e.target.value)}
                    placeholder="jane@enterprise.com"
                    className="w-full bg-slate-50 dark:bg-canvas-dark border border-slate-300 dark:border-terminal-subtle px-3 py-2 text-xs text-slate-900 dark:text-slate-100 focus:outline-none focus:border-cobalt-600 dark:focus:border-cobalt-400 font-mono rounded-sm"
                  />
                </div>
              </div>

              <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
                <div>
                  <label className="block text-xs font-mono font-medium text-slate-700 dark:text-slate-300 mb-1">
                    Company / Importer Name *
                  </label>
                  <input
                    type="text"
                    required
                    value={companyName}
                    onChange={(e) => setCompanyName(e.target.value)}
                    placeholder="Apex Global Logistics"
                    className="w-full bg-slate-50 dark:bg-canvas-dark border border-slate-300 dark:border-terminal-subtle px-3 py-2 text-xs text-slate-900 dark:text-slate-100 focus:outline-none focus:border-cobalt-600 dark:focus:border-cobalt-400 font-mono rounded-sm"
                  />
                </div>

                <div>
                  <label className="block text-xs font-mono font-medium text-slate-700 dark:text-slate-300 mb-1">
                    Direct Phone / Cell
                  </label>
                  <input
                    type="tel"
                    value={phone}
                    onChange={(e) => setPhone(e.target.value)}
                    placeholder="+1 (555) 234-5678"
                    className="w-full bg-slate-50 dark:bg-canvas-dark border border-slate-300 dark:border-terminal-subtle px-3 py-2 text-xs text-slate-900 dark:text-slate-100 focus:outline-none focus:border-cobalt-600 dark:focus:border-cobalt-400 font-mono rounded-sm"
                  />
                </div>
              </div>

              <div>
                <label className="block text-xs font-mono font-medium text-slate-700 dark:text-slate-300 mb-1">
                  Monthly Document Volume (bills, entries, XML shipments)
                </label>
                <select
                  value={volume}
                  onChange={(e) => setVolume(e.target.value)}
                  className="w-full bg-slate-50 dark:bg-canvas-dark border border-slate-300 dark:border-terminal-subtle px-3 py-2 text-xs text-slate-900 dark:text-slate-100 focus:outline-none focus:border-cobalt-600 dark:focus:border-cobalt-400 font-mono rounded-sm"
                >
                  <option value="&lt;500 documents/mo">&lt; 500 documents per month</option>
                  <option value="500-2500 documents/mo">500 - 2,500 documents per month</option>
                  <option value="2500-10000 documents/mo">2,500 - 10,000 documents per month</option>
                  <option value="10000+ documents/mo">10,000+ documents per month (Enterprise)</option>
                </select>
              </div>

              {/* Privacy Policy Consent Checkbox & Inline Notice Drawer (Finding M13) */}
              <div className="pt-1 space-y-2">
                <label className="flex items-start gap-2 cursor-pointer text-xs font-mono text-slate-700 dark:text-slate-300">
                  <input
                    type="checkbox"
                    required
                    checked={privacyConsent}
                    onChange={(e) => setPrivacyConsent(e.target.checked)}
                    className="mt-0.5 rounded border-slate-300 dark:border-slate-700 text-cobalt-600 focus:ring-cobalt-500"
                  />
                  <span>
                    I agree to the privacy terms for technical review contact. Read our{" "}
                    <button
                      type="button"
                      aria-expanded={showPrivacyNotice}
                      aria-controls="inline-privacy-notice-drawer"
                      onClick={() => setShowPrivacyNotice((prev) => !prev)}
                      className="text-cobalt-600 dark:text-cobalt-400 underline hover:text-cobalt-500 font-semibold"
                    >
                      privacy and data retention notice
                    </button>
                    .
                  </span>
                </label>

                {showPrivacyNotice && (
                  <div
                    id="inline-privacy-notice-drawer"
                    role="region"
                    aria-label="Privacy and Data Retention Notice"
                    className="p-3 bg-slate-50 dark:bg-canvas-dark border border-slate-200 dark:border-terminal-subtle rounded-sm text-[11px] font-mono text-slate-600 dark:text-slate-300 space-y-1.5 leading-relaxed"
                  >
                    <p>
                      <strong className="text-slate-900 dark:text-slate-100">Data Controller:</strong> Samuel, Principal Architect, TradeTech Systems Studio.
                    </p>
                    <p>
                      <strong className="text-slate-900 dark:text-slate-100">Purpose:</strong> Used exclusively to schedule and follow up on your requested technical architecture review. Zero marketing resale, zero third-party brokerage, and zero unconsented telemetry.
                    </p>
                    <p>
                      <strong className="text-slate-900 dark:text-slate-100">Retention Period:</strong> Deleted automatically within 90 days after inquiry closure unless an active NDA engagement is initiated.
                    </p>
                    <p>
                      <strong className="text-slate-900 dark:text-slate-100">Opt-Out &amp; Erasure:</strong> Email{" "}
                      <a
                        href="mailto:samuel-tradetech@outlook.com?subject=Data%20Deletion%20Request"
                        className="text-cobalt-600 dark:text-cobalt-400 underline"
                      >
                        samuel-tradetech@outlook.com
                      </a>{" "}
                      at any time for immediate removal.
                    </p>
                  </div>
                )}
              </div>

              <div className="pt-2">
                <button
                  type="submit"
                  disabled={isSubmitting || !privacyConsent}
                  className="w-full py-3 px-4 bg-cobalt-600 hover:bg-cobalt-500 dark:bg-cobalt-500 dark:hover:bg-cobalt-400 text-canvas-stone dark:text-slate-950 font-bold font-mono text-xs uppercase tracking-wider flex items-center justify-center gap-2 transition-colors disabled:opacity-50 rounded-sm cursor-pointer disabled:cursor-not-allowed"
                >
                  {isSubmitting ? (
                    <>
                      <Loader2 className="w-4 h-4 animate-spin" />
                      <span>Transmitting Review Request...</span>
                    </>
                  ) : (
                    <>
                      <span>Request Architecture Review</span>
                      <ArrowRight className="w-4 h-4" />
                    </>
                  )}
                </button>
              </div>

              <div className="flex flex-col sm:flex-row items-center justify-center gap-2 sm:gap-4 text-[10px] font-mono text-slate-400 pt-1">
                <span className="flex items-center gap-1">
                  <Shield className="w-3 h-3 text-cobalt-600 dark:text-cobalt-400" />
                  <span>NDA on Request : Zero Data Retention</span>
                </span>
                <span className="hidden sm:inline">•</span>
                <span>Zero Cloud OCR Retention</span>
              </div>
            </form>
          </div>
        ) : (
          <div className="py-4 text-center">
            <div className="w-12 h-12 bg-emerald-100 dark:bg-emerald-950/60 border border-emerald-300 dark:border-emerald-500/60 text-emerald-600 dark:text-emerald-400 flex items-center justify-center mx-auto mb-3 rounded-full">
              <CheckCircle2 className="w-6 h-6" />
            </div>

            <h3
              id="lead-capture-modal-title"
              className="text-lg font-bold text-slate-900 dark:text-slate-100 mb-1"
            >
              Review Request Logged
            </h3>
            <p className="text-xs text-slate-600 dark:text-slate-300 leading-relaxed mb-4 max-w-sm mx-auto">
              Your request has been logged. Samuel will review your document volume profile and reach out within 4 business hours to schedule the working session.
            </p>

            <div className="p-3 bg-slate-50 dark:bg-canvas-dark border border-slate-200 dark:border-terminal-subtle text-left text-xs font-mono text-slate-600 dark:text-slate-400 space-y-1 mb-5 rounded-sm">
              <div className="flex justify-between">
                <span>Reference ID:</span>
                <span className="text-cobalt-600 dark:text-cobalt-400 font-semibold">{leadId}</span>
              </div>
              <div className="flex justify-between">
                <span>Session Lead:</span>
                <span className="text-slate-900 dark:text-slate-200 font-medium">Samuel | Principal Architect</span>
              </div>
              <div className="flex justify-between">
                <span>Response Window:</span>
                <span className="text-emerald-700 dark:text-emerald-400 font-bold">4 Business Hours</span>
              </div>
            </div>

            <button
              onClick={onClose}
              className="px-6 py-2.5 bg-slate-900 hover:bg-slate-800 dark:bg-terminal-elevated dark:hover:bg-terminal-elevated text-xs font-mono text-canvas-stone dark:text-slate-200 border border-slate-700 dark:border-terminal-border transition-colors rounded-sm"
            >
              Return to Workbench
            </button>
          </div>
        )}
      </div>
    </div>
  );
};
