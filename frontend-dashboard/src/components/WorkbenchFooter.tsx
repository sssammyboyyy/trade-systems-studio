"use client";

import React from "react";
import { ArrowRight, Lock } from "lucide-react";

interface WorkbenchFooterProps {
  onOpenReview: () => void;
}

export const WorkbenchFooter: React.FC<WorkbenchFooterProps> = ({
  onOpenReview,
}) => {
  return (
    <footer className="border-t border-terminal-subtle bg-terminal-slate py-10 mt-12 type-mono-data text-ink-muted">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 flex flex-col md:flex-row items-center justify-between gap-6">
        <div className="max-w-xl text-center md:text-left">
          <h3 className="type-heading-sm text-ink-primary mb-1">
            Trade Systems Studio: Deterministic Trade Compliance Engineering
          </h3>
          <p className="type-body-dense text-ink-muted">
            Built and maintained by Samuel Rencken. Every statutory figure computed in Python Decimal, every finding traceable to its source clause.
          </p>
        </div>

        <div className="flex items-center gap-3">
          <button
            onClick={onOpenReview}
            className="px-5 py-2.5 bg-cobalt-600 hover:bg-cobalt-500 text-canvas-stone font-semibold font-mono text-xs uppercase tracking-wider flex items-center gap-2 transition-colors rounded-md"
          >
            <span>Schedule Architecture Review</span>
            <ArrowRight className="w-3.5 h-3.5" />
          </button>
        </div>
      </div>

      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 mt-8 pt-6 border-t border-terminal-subtle flex flex-col sm:flex-row items-center justify-between gap-4">
        <div>
          © {new Date().getFullYear()} Samuel Rencken · Trade Systems Studio. All rights reserved.
        </div>
        <div className="flex items-center gap-4">
          <span className="flex items-center gap-1">
            <Lock className="w-3 h-3 text-slate-400" />
            <span>NDA Available on Request</span>
          </span>
          <span>·</span>
          <span>Zero Cloud OCR Retention</span>
        </div>
      </div>
    </footer>
  );
};
