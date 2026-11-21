"use client";

import React, { useState } from "react";
import { motion } from "framer-motion";
import { Discrepancy } from "@/lib/types";

import { formatUsd, gtZero } from "@/lib/money";
import { TabularAmount } from "./TabularAmount";
import { AlertOctagon, AlertTriangle, ShieldCheck, ArrowUpRight, ChevronDown, ChevronUp, Scale, Crosshair } from "lucide-react";

interface DiscrepancyCardProps {
  discrepancy: Discrepancy;
  isActive: boolean;
  onHover: (id: string | null) => void;
  onClick: (id: string) => void;
  onFocusMobileDoc?: () => void;
}

export const DiscrepancyCard: React.FC<DiscrepancyCardProps> = ({
  discrepancy,
  isActive,
  onHover,
  onClick,
  onFocusMobileDoc,
}) => {
  const [showCitation, setShowCitation] = useState(false);
  const isUncertain = discrepancy.confidence < 0.85;

  const getSeverityStyle = () => {
    switch (discrepancy.severity) {
      case "critical":
        return {
          badge:
            "bg-red-500/10 text-ink-crimson border-red-500/30",
          icon: <AlertOctagon className="w-4 h-4 text-ink-crimson shrink-0" />,
          accent: "text-ink-crimson",
          highlightBg: "hover:border-red-500/50",
        };
      case "opportunity":
        return {
          badge:
            "bg-emerald-500/10 text-ink-emerald border-emerald-500/30",
          icon: <ShieldCheck className="w-4 h-4 text-ink-emerald shrink-0" />,
          accent: "text-ink-emerald",
          highlightBg: "hover:border-emerald-500/50",
        };
      case "warning":
      default:
        return {
          badge:
            "bg-amber-500/10 text-ink-amber border-amber-500/30",
          icon: <AlertTriangle className="w-4 h-4 text-ink-amber shrink-0" />,
          accent: "text-ink-amber",
          highlightBg: "hover:border-amber-500/50",
        };
    }
  };

  const style = getSeverityStyle();

  return (
    <motion.div
      initial={{ opacity: 0.85, rotateX: -12 }}
      whileInView={{ opacity: 1, rotateX: 0 }}
      viewport={{ once: true, margin: "-20px" }}
      transition={{
        type: "spring",
        stiffness: 340,
        damping: 32,
        mass: 0.8,
      }}
      style={{ perspective: 1200, transformStyle: "preserve-3d" }}
      className="relative will-change-transform"
    >
      <div
        id={`card-${discrepancy.id}`}
        role="button"
        tabIndex={0}
        aria-pressed={isActive}
        aria-label={`Discrepancy: ${discrepancy.title}, exposure: ${
          gtZero(discrepancy.exposure_amount)
            ? formatUsd(discrepancy.exposure_amount)
            : "Valuation defect"
        }`}
        onKeyDown={(e) => {
          if (e.target !== e.currentTarget) return;
          if (e.key === "Enter" || e.key === " ") {
            e.preventDefault();
            onClick(discrepancy.id);
          }
        }}
        onMouseEnter={() => onHover(discrepancy.id)}
        onMouseLeave={() => onHover(null)}
        onClick={() => onClick(discrepancy.id)}
        className={`relative p-4 transition-all duration-300 ease-[cubic-bezier(0.16,1,0.3,1)] active:scale-[0.985] cursor-pointer border rounded-lg overflow-hidden focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-blue-400 ${
          isActive
            ? "bg-terminal-elevated border-blue-500 ring-1 ring-blue-500 shadow-xl shadow-blue-500/10"
            : isUncertain
            ? "bg-terminal-slate border-dashed border-amber-500/70 hover:border-amber-400"
            : `bg-terminal-slate border-terminal-subtle ${style.highlightBg}`
        }`}
      >
        {/* iPhone Duo 3D Crease Shadow Overlay */}
        <div className="absolute inset-0 bg-gradient-to-b from-black/25 via-transparent to-black/15 pointer-events-none rounded-lg" />

        {/* Top Metadata Strip */}
        <div className="relative z-10 flex items-center justify-between gap-2 mb-2">
          <div className="flex items-center gap-2">
            {style.icon}
            <span
              className={`type-caption-mono uppercase px-2 py-0.5 border rounded-md ${style.badge}`}
            >
              {discrepancy.severity}
            </span>
            <span className="statutory-cite text-[12px] text-ink-statutory bg-slate-900/60 px-2 py-0.5 border border-slate-800 rounded-md">
              {discrepancy.statutory_code}
            </span>
          </div>

          {/* Confidence Telemetry */}
          <div className="flex items-center gap-1.5 type-caption-mono tabular-nums text-ink-muted">
            <span className={isUncertain ? "text-ink-amber font-medium" : "text-ink-muted"}>
              {(discrepancy.confidence * 100).toFixed(0)}% CONF
            </span>
            {isUncertain && (
              <span className="flex h-2 w-2 relative">
                <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-amber-400 opacity-75"></span>
                <span className="relative inline-flex rounded-full h-2 w-2 bg-amber-400"></span>
              </span>
            )}
          </div>
        </div>

        {/* Discrepancy Title */}
        <h3 className="relative z-10 type-heading-sm text-ink-primary mb-1 flex items-start justify-between gap-2">
          <span>{discrepancy.title}</span>
          <ArrowUpRight className="w-3.5 h-3.5 text-ink-muted shrink-0 mt-1" />
        </h3>

        {/* Concise Summary / Core Finding */}
        <p className="relative z-10 type-body-dense text-ink-secondary mb-2 line-clamp-2">
          {discrepancy.executive_summary || discrepancy.description}
        </p>

        {/* Financial Blast Radius Line */}
        <div className="relative z-10 flex items-center justify-between pt-2 border-t border-slate-800">
          <span className="type-caption-mono uppercase text-ink-muted">
            {discrepancy.severity === "opportunity"
              ? "Recoverable Cash Margin"
              : "Statutory Financial Exposure"}
          </span>
          <span className={`type-mono-data text-sm font-medium ${style.accent}`}>
            {gtZero(discrepancy.exposure_amount) ? (
              <TabularAmount value={discrepancy.exposure_amount} />
            ) : (
              "Valuation Defect"
            )}
          </span>
        </div>

        {/* Progressive Disclosure: Collapsible Statutory Legal Citation */}
        <div className="relative z-10 mt-2.5 pt-2 border-t border-slate-800/60">
          <button
            type="button"
            aria-expanded={showCitation}
            aria-controls={`citation-${discrepancy.id}`}
            onClick={(e) => {
              e.stopPropagation();
              setShowCitation(!showCitation);
            }}
            className="w-full flex items-center justify-between type-caption-mono text-ink-cobalt hover:text-cobalt-300 transition-colors cursor-pointer"
          >
            <span className="flex items-center gap-1.5 font-medium">
              <Scale className="w-3 h-3" />
              <span>Read Statutory Citation & Analysis</span>
            </span>
            {showCitation ? (
              <ChevronUp className="w-3.5 h-3.5" />
            ) : (
              <ChevronDown className="w-3.5 h-3.5" />
            )}
          </button>

          {showCitation && (
            <div id={`citation-${discrepancy.id}`} className="mt-2 p-2.5 bg-slate-950/80 border border-slate-800 type-body-dense text-ink-secondary rounded-md space-y-2">
              <p className="statutory-cite border-l-2 border-cobalt-500 pl-2">
                {discrepancy.description}
              </p>
              {discrepancy.statutory_defense && (
                <div className="pt-1.5 border-t border-slate-800">
                  <span className="font-medium text-ink-cobalt block mb-0.5 type-caption-mono uppercase">
                    Remediation Protocol:
                  </span>
                  <p className="type-body-dense text-ink-secondary">{discrepancy.statutory_defense}</p>
                </div>
              )}
            </div>
          )}
        </div>

        {/* Mobile & Tablet Locate on PDF Button with Pseudo-Haptic Recoil */}
        {onFocusMobileDoc && (
          <button
            type="button"
            onClick={(e) => {
              e.stopPropagation();
              onFocusMobileDoc();
            }}
            className="lg:hidden relative z-10 mt-2.5 w-full py-2 px-3 bg-blue-950/80 hover:bg-blue-900/80 active:scale-[0.98] text-blue-300 border border-blue-700/60 hover:border-blue-500 text-xs font-mono font-semibold flex items-center justify-center gap-2 rounded-md transition-all shadow-xs"
          >
            <Crosshair className="w-3.5 h-3.5 text-blue-400" />
            <span>Locate on Source PDF</span>
          </button>
        )}
      </div>
    </motion.div>
  );
};
