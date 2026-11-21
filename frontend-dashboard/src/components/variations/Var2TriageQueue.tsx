"use client";

import React, { useState, useEffect, useRef, useMemo } from "react";
import { useVirtualizer } from "@tanstack/react-virtual";
import { usePreIngestFirewall, playPseudoHaptic } from "@/lib/firewall-core";
import { ThreeWayResolutionBar } from "../ThreeWayResolutionBar";
import { TabularAmount } from "../TabularAmount";

import { resolveAssetPath } from "@/lib/assets";
import { MOCK_AUDIT_DATA } from "@/data/mockData";
import { Clock, Filter, Search, Command, X, ExternalLink, ChevronRight } from "lucide-react";

export type OwnerRoute = "all" | "broker_desk" | "ap_carrier_dispute" | "shipper_outreach";

export interface TriageInvoiceRow {
  id: string;
  entryNumber: string;
  carrier: string;
  corridor: string;
  ownerRoute: "broker_desk" | "ap_carrier_dispute" | "shipper_outreach";
  statutoryCode: string;
  discrepancyTitle: string;
  discrepancyDescription: string;
  exposureAmount: number;
  confidence: number;
  severity: "critical" | "warning" | "opportunity";
  cutoffSeconds: number;
  status: "QUARANTINED" | "RELEASED" | "ESCALATED";
  pdfFilename?: string;
  yenteEntityId?: string;
  yenteMatchScore?: number;
  ownershipPath?: string;
}

// Deterministic generator of 500 realistic commercial invoice triage records
const CARRIERS = [
  "PACIFIC HORIZON LINES",
  "ATLANTIC CREST OCEAN",
  "BEACON GLOBAL FORWARDING",
  "FICTIONAL PACIFIC LINES",
  "ZENITH MARITIME LOGISTICS",
  "NORDIC CARGO FREIGHT",
  "SOLARIS SEAWAYS",
  "VANGUARD CONTAINER LINES",
];

const CORRIDORS = [
  "YTN -> LAX (Transpacific)",
  "DUR -> RTM (Cape Hope)",
  "SHA -> LGB (Transpacific)",
  "HAM -> NYC (Transatlantic)",
  "SIN -> DXB (Indian Ocean)",
  "BUS -> OAK (Transpacific)",
];

const STATUTORY_CONFIGS = [
  {
    ownerRoute: "broker_desk" as const,
    statutoryCode: "19 U.S.C. § 1592",
    title: "Unreported Dutiable Assist & Freight Deductible Overstatement",
    description: "Buyer supplied offshore production tooling without 19 CFR § 152.103 customs assist declaration.",
    severity: "critical" as const,
    baseAmount: 62500,
    confidenceBase: 0.74,
  },
  {
    ownerRoute: "ap_carrier_dispute" as const,
    statutoryCode: "46 CFR 545.5 / Part 541",
    title: "Unauthorized Dual Chassis Split & Inflated Bunker Surcharge",
    description: "Detention billed for days the terminal was closed, with no chassis work order on file.",
    severity: "warning" as const,
    baseAmount: 1547.5,
    confidenceBase: 0.92,
  },
  {
    ownerRoute: "shipper_outreach" as const,
    statutoryCode: "19 CFR § 152.103",
    title: "Missing Destination Inland Freight Certificate & Commercial Invoice Addendum",
    description: "Original clean Ocean Bill of Lading lacks inland apportioned freight breakdown required for CIF deduction.",
    severity: "warning" as const,
    baseAmount: 4320,
    confidenceBase: 0.68,
  },
  {
    ownerRoute: "broker_desk" as const,
    statutoryCode: "WCO GRI 1 to 6",
    title: "Drone Rotor Assembly Subheading Discordance (8501.31 vs 8807.30)",
    description: "Component classification requires essential character verification under General Rules of Interpretation.",
    severity: "warning" as const,
    baseAmount: 18450,
    confidenceBase: 0.79,
  },
  {
    ownerRoute: "broker_desk" as const,
    statutoryCode: "31 CFR § 501 / OFAC 50%",
    title: "Beneficial Ownership Screening Alert: Second-Tier Holding Entity",
    description: "Consignee shareholder graph resolved 50% cumulative ownership linked to SDN List designated entity.",
    severity: "critical" as const,
    baseAmount: 95000,
    confidenceBase: 0.88,
  },
  {
    ownerRoute: "ap_carrier_dispute" as const,
    statutoryCode: "19 U.S.C. § 1313",
    title: "Unclaimed Direct Duty Drawback Match: Export Bill of Lading Pair",
    description: "Identified eligible 99% duty refund on imported alloy goods subsequently re-exported without transformation.",
    severity: "opportunity" as const,
    baseAmount: 27324,
    confidenceBase: 0.96,
  },
];

const amt = (concept: string, key: "penalty_exposure_avoided" | "carrier_overbilling_caught" | "drawback_unclaimed_unlocked") =>
  Number(MOCK_AUDIT_DATA[concept]?.metrics[key] ?? 0);

// Rows 1-4 are the bundled sample documents with their engine results; rows 5-500 are a
// synthetic queue (seeded, deterministic) used to exercise virtualised triage at volume.
function generate500Invoices(): TriageInvoiceRow[] {
  const rows: TriageInvoiceRow[] = [
    {
      id: "DISC-ROW-0001",
      entryNumber: "CBP-7501-8841-01",
      carrier: "PACIFIC HORIZON LINES",
      corridor: "YTN -> LAX (Transpacific)",
      ownerRoute: "broker_desk",
      statutoryCode: "19 U.S.C. § 1592",
      discrepancyTitle: "Processor Declared Under 8471.30, Line Arithmetic Error, CIF Freight Not Deducted",
      discrepancyDescription: "Sample invoice SSAC-2024-89912: AI processors declared under 8471.30 (no Section 301 duty) rather than 8542.31 (25% in April 2024); line 1 extension overstated by $3,000; ocean freight left in a CIF total. Amount is the 19 U.S.C. § 1592(c)(3) negligence maximum.",
      exposureAmount: amt("concept_1_customs", "penalty_exposure_avoided"),
      confidence: 0.82,
      severity: "critical",
      cutoffSeconds: 14 * 3600 - 120,
      status: "QUARANTINED",
      pdfFilename: "nightmare_01_customs_ci.pdf",
    },
    {
      id: "DISC-ROW-0002",
      entryNumber: "BOL-MEDU-9921-02",
      carrier: "MSC MEDITERRANEAN",
      corridor: "SHA -> LGB (Transpacific)",
      ownerRoute: "ap_carrier_dispute",
      statutoryCode: "46 CFR 545.5 / Part 541",
      discrepancyTitle: "Fuel Surcharge Above Contract, Chassis Split Without Work Order, Detention Inside Free Time",
      discrepancyDescription: "Sample freight invoice PACL-FRT-982104: FSC billed at 32.5% vs 24.0% contracted, $285 chassis split with no work order, and $880 detention billed although the container out-gated on day 5 of 5 free days.",
      exposureAmount: amt("concept_2_freight", "carrier_overbilling_caught"),
      confidence: 0.94,
      severity: "warning",
      cutoffSeconds: 14 * 3600 - 450,
      status: "QUARANTINED",
      pdfFilename: "nightmare_02_freight_audit.pdf",
    },
    {
      id: "DISC-ROW-0003",
      entryNumber: "CBP-7501-DRAW-03",
      carrier: "COSCO SHIPPING",
      corridor: "BUS -> OAK (Transpacific)",
      ownerRoute: "ap_carrier_dispute",
      statutoryCode: "19 U.S.C. § 1313",
      discrepancyTitle: "Unclaimed 99% Direct Identification Duty Drawback on Export BOL",
      discrepancyDescription: "Sample claim: 1,000 units imported on entry CBP-7501-84920184 (Jan 2024) matched by serial range to export B/L BGFU-0941824 (Mar 2024), inside the 5-year limit.",
      exposureAmount: amt("concept_3_drawback", "drawback_unclaimed_unlocked"),
      confidence: 0.97,
      severity: "opportunity",
      cutoffSeconds: 14 * 3600 - 900,
      status: "RELEASED",
      pdfFilename: "nightmare_03_duty_drawback.pdf",
    },
    {
      id: "DISC-ROW-0004",
      entryNumber: "OFAC-501-SDN-04",
      carrier: "HAPAG-LLOYD",
      corridor: "HAM -> NYC (Transatlantic)",
      ownerRoute: "broker_desk",
      statutoryCode: "31 CFR § 501 / OFAC 50%",
      discrepancyTitle: "Blocked Entity Corporate Hierarchy: 55% Aggregate SDN Ownership",
      discrepancyDescription: "Target entity bis-el-cn-0941 owned 25% by Victor Petrov (SDN) and 30% by Rosoboronexport JSC (SDN). Blocked by operation of law under OFAC 50% Rule.",
      exposureAmount: amt("concept_4_sanctions", "penalty_exposure_avoided"),
      confidence: 0.99,
      severity: "critical",
      cutoffSeconds: 14 * 3600 - 300,
      status: "QUARANTINED",
      pdfFilename: "nightmare_04_ofac_registry.pdf",
      yenteEntityId: "bis-el-cn-0941",
      yenteMatchScore: 98.5,
      ownershipPath: "Victor Petrov (25% SDN) + Rosoboronexport JSC (30% SDN) -> 55.0% Blocked",
    },
  ];

  for (let i = 5; i <= 500; i++) {
    const config = STATUTORY_CONFIGS[i % STATUTORY_CONFIGS.length];
    const carrier = CARRIERS[i % CARRIERS.length];
    const corridor = CORRIDORS[i % CORRIDORS.length];
    const padId = String(i).padStart(4, "0");
    const entryNumber = `CBP-7501-${padId}-${(i * 17) % 99}`;
    
    // Vary amounts and confidences deterministically
    const exposureAmount = Math.round((config.baseAmount * (0.8 + ((i * 7) % 50) / 100)) * 100) / 100;
    const confidence = Math.min(0.99, Math.max(0.62, Math.round((config.confidenceBase + ((i % 13) - 6) * 0.02) * 100) / 100));
    const cutoffSeconds = 14 * 3600 - (i * 73) % (14 * 3600 - 300);

    rows.push({
      id: `DISC-ROW-${padId}`,
      entryNumber,
      carrier,
      corridor,
      ownerRoute: config.ownerRoute,
      statutoryCode: config.statutoryCode,
      discrepancyTitle: `${config.title} (#${padId})`,
      discrepancyDescription: config.description,
      exposureAmount,
      confidence,
      severity: config.severity,
      cutoffSeconds,
      status: confidence < 0.85 || config.severity === "critical" ? "QUARANTINED" : "RELEASED",
    });
  }
  return rows;
}

export const Var2TriageQueue: React.FC = () => {
  const { resolutionHistory } = usePreIngestFirewall();
  const allRows = useMemo(() => generate500Invoices(), []);

  // Filter state
  const [activeOwnerFilter, setActiveOwnerFilter] = useState<OwnerRoute>("all");
  const [searchQuery, setSearchQuery] = useState<string>("");
  const [isCommandBarOpen, setIsCommandBarOpen] = useState<boolean>(false);
  const [selectedIndex, setSelectedIndex] = useState<number>(0);
  const [inspectedRow, setInspectedRow] = useState<TriageInvoiceRow | null>(null);

  // Live Carrier Cutoff Countdown (starts at 14:00:00 and ticks down every second)
  const [countdownSeconds, setCountdownSeconds] = useState<number>(14 * 3600);

  useEffect(() => {
    const timer = setInterval(() => {
      setCountdownSeconds((prev) => (prev > 0 ? prev - 1 : 0));
    }, 1000);
    return () => clearInterval(timer);
  }, []);

  const formatCountdown = (totalSeconds: number) => {
    const hrs = Math.floor(totalSeconds / 3600);
    const mins = Math.floor((totalSeconds % 3600) / 60);
    const secs = totalSeconds % 60;
    return `${String(hrs).padStart(2, "0")}:${String(mins).padStart(2, "0")}:${String(secs).padStart(2, "0")}`;
  };

  // Filtered rows
  const filteredRows = useMemo(() => {
    return allRows.filter((row) => {
      if (activeOwnerFilter !== "all" && row.ownerRoute !== activeOwnerFilter) {
        return false;
      }
      if (searchQuery.trim()) {
        const q = searchQuery.toLowerCase();
        return (
          row.entryNumber.toLowerCase().includes(q) ||
          row.carrier.toLowerCase().includes(q) ||
          row.statutoryCode.toLowerCase().includes(q) ||
          row.discrepancyTitle.toLowerCase().includes(q)
        );
      }
      return true;
    });
  }, [allRows, activeOwnerFilter, searchQuery]);

  // Virtualizer setup
  const parentRef = useRef<HTMLDivElement>(null);
  const rowVirtualizer = useVirtualizer({
    count: filteredRows.length,
    getScrollElement: () => parentRef.current,
    estimateSize: () => 56,
    overscan: 10,
  });

  // Keyboard navigation: J, K, Enter, ⌘K
  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      // ⌘K or Ctrl+K for Command Bar
      if ((e.metaKey || e.ctrlKey) && e.key.toLowerCase() === "k") {
        e.preventDefault();
        playPseudoHaptic();
        setIsCommandBarOpen((prev) => !prev);
        return;
      }

      // If command bar or text input is focused, don't intercept J/K
      if (isCommandBarOpen || (e.target as HTMLElement).tagName === "INPUT") {
        if (e.key === "Escape") {
          setIsCommandBarOpen(false);
          setInspectedRow(null);
        }
        return;
      }

      if (e.key === "j" || e.key === "ArrowDown") {
        e.preventDefault();
        playPseudoHaptic();
        setSelectedIndex((prev) => {
          const next = Math.min(filteredRows.length - 1, prev + 1);
          rowVirtualizer.scrollToIndex(next, { align: "auto" });
          return next;
        });
      } else if (e.key === "k" || e.key === "ArrowUp") {
        e.preventDefault();
        playPseudoHaptic();
        setSelectedIndex((prev) => {
          const next = Math.max(0, prev - 1);
          rowVirtualizer.scrollToIndex(next, { align: "auto" });
          return next;
        });
      } else if (e.key === "Enter") {
        e.preventDefault();
        playPseudoHaptic();
        if (filteredRows[selectedIndex]) {
          setInspectedRow(filteredRows[selectedIndex]);
        }
      } else if (e.key === "Escape") {
        setInspectedRow(null);
      }
    };

    window.addEventListener("keydown", handleKeyDown);
    return () => window.removeEventListener("keydown", handleKeyDown);
  }, [filteredRows, selectedIndex, isCommandBarOpen, rowVirtualizer]);

  return (
    <div className="w-full max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-6 space-y-4 font-sans text-ink-primary">
      {/* 1. TOP OPERATOR CONTROL BAR */}
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-4 p-4 rounded-xl bg-terminal-slate border border-terminal-subtle shadow-xl">
        {/* Live Carrier Cutoff Countdown Banner */}
        <div className="flex items-center gap-3">
          <div className="p-2.5 rounded-lg bg-red-950/60 border border-red-800/80 text-ink-crimson flex items-center justify-center shrink-0">
            <Clock className="w-5 h-5 animate-pulse" />
          </div>
          <div>
            <div className="flex items-center gap-2">
              <span className="type-caption-mono uppercase text-ink-muted font-medium">
                Carrier cutoff (demo clock)
              </span>
              <span className="inline-block w-2 h-2 rounded-full bg-red-400 animate-ping" />
            </div>
            <div className="type-display-md font-mono text-ink-crimson tabular-nums">
              {formatCountdown(countdownSeconds)}
            </div>
          </div>
        </div>

        {/* Keyboard Quick Command Instructions */}
        <div className="hidden xl:flex items-center gap-2 font-mono text-xs text-slate-400 bg-canvas-dark px-3 py-2 rounded-lg border border-terminal-subtle">
          <span>TRIAGE HOTKEYS:</span>
          <kbd className="px-1.5 py-0.5 rounded bg-terminal-elevated border border-terminal-border text-slate-200">J</kbd>
          <span>Next</span>
          <kbd className="px-1.5 py-0.5 rounded bg-terminal-elevated border border-terminal-border text-slate-200">K</kbd>
          <span>Prev</span>
          <kbd className="px-1.5 py-0.5 rounded bg-terminal-elevated border border-terminal-border text-slate-200">Enter</kbd>
          <span>Inspect</span>
          <kbd className="px-1.5 py-0.5 rounded bg-terminal-elevated border border-terminal-border text-slate-200">⌘K</kbd>
          <span>Command</span>
        </div>

        {/* Search & Command Trigger */}
        <div className="flex items-center gap-2">
          <div className="relative">
            <Search className="w-4 h-4 text-slate-400 absolute left-3 top-1/2 -translate-y-1/2" />
            <input
              type="text"
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              placeholder="Search 500 invoices (4 samples + synthetic)"
              className="pl-9 pr-4 py-2 bg-canvas-dark border border-terminal-subtle rounded-lg text-xs font-mono text-slate-200 placeholder:text-slate-400 focus:outline-none focus:border-blue-500 w-48 sm:w-64"
            />
          </div>
          <button
            onClick={() => {
              playPseudoHaptic();
              setIsCommandBarOpen(true);
            }}
            className="flex items-center gap-1.5 px-3 py-2 rounded-lg bg-terminal-elevated hover:bg-slate-700 border border-terminal-border text-xs font-mono text-slate-200 transition-colors"
            title="Open Command Palette (⌘K)"
          >
            <Command className="w-3.5 h-3.5" />
            <span className="hidden sm:inline">Cmd</span>
            <span className="text-[10px] text-slate-400 font-bold">⌘K</span>
          </button>
        </div>
      </div>

      {/* 2. OWNER-ROUTED FILTER CHIPS */}
      <div className="flex items-center gap-2 overflow-x-auto pb-1 scrollbar-thin">
        <span className="text-[10px] font-mono text-slate-400 uppercase font-bold shrink-0 mr-1 flex items-center gap-1">
          <Filter className="w-3 h-3" />
          <span>ROUTING:</span>
        </span>

        {[
          { id: "all", label: "All Queues", count: allRows.length },
          { id: "broker_desk", label: "Broker Desk", count: allRows.filter((r) => r.ownerRoute === "broker_desk").length },
          { id: "ap_carrier_dispute", label: "AP Carrier Dispute", count: allRows.filter((r) => r.ownerRoute === "ap_carrier_dispute").length },
          { id: "shipper_outreach", label: "Shipper Outreach", count: allRows.filter((r) => r.ownerRoute === "shipper_outreach").length },
        ].map((chip) => {
          const isActive = activeOwnerFilter === chip.id;
          return (
            <button
              key={chip.id}
              onClick={() => {
                playPseudoHaptic();
                setActiveOwnerFilter(chip.id as OwnerRoute);
                setSelectedIndex(0);
              }}
              className={`flex items-center gap-1.5 px-3 py-1.5 rounded-lg border type-mono-data whitespace-nowrap transition-colors ${
                isActive
                  ? "bg-cobalt-600 border-cobalt-400 text-canvas-stone font-medium shadow-md shadow-blue-600/20"
                  : "bg-terminal-slate border-terminal-subtle text-ink-muted hover:text-ink-primary hover:bg-terminal-elevated"
              }`}
            >
              <span>{chip.label}</span>
              <span
                className={`text-[10px] px-1.5 py-0.2 rounded-full ${
                  isActive ? "bg-blue-700 text-blue-100" : "bg-terminal-elevated text-slate-400"
                }`}
              >
                {chip.count}
              </span>
            </button>
          );
        })}
      </div>

      {/* 3. VIRTUALIZED 500-ROW TRIAGE TABLE */}
      <div className="rounded-xl border border-terminal-subtle bg-terminal-slate overflow-hidden shadow-2xl">
        <div className="overflow-x-auto">
          <div className="min-w-[1020px]">
            {/* Table Header */}
            <div className="grid grid-cols-12 gap-2 px-4 py-3 bg-canvas-dark border-b border-terminal-subtle text-[10px] font-mono text-slate-400 uppercase font-semibold">
              <div className="col-span-1">#</div>
              <div className="col-span-2">Entry & Carrier</div>
              <div className="col-span-2">Corridor</div>
              <div className="col-span-3">Statutory Finding</div>
              <div className="col-span-1 text-right">Exposure</div>
              <div className="col-span-1 text-center">Confidence</div>
              <div className="col-span-2 text-center">Status & Action</div>
            </div>

            {/* Virtual List Container */}
            <div
              ref={parentRef}
              className="h-[580px] overflow-y-auto divide-y divide-terminal-subtle/60 scrollbar-thin font-mono text-xs"
            >
              {filteredRows.length === 0 ? (
                <div className="flex flex-col items-center justify-center h-48 text-slate-400 text-xs">
                  <span>No invoices matched the active query.</span>
                </div>
              ) : (
                <div
                  style={{
                    height: `${rowVirtualizer.getTotalSize()}px`,
                    width: "100%",
                    minWidth: "1020px",
                    position: "relative",
                  }}
                >
              {rowVirtualizer.getVirtualItems().map((virtualRow) => {
                const row = filteredRows[virtualRow.index];
                const isSelected = selectedIndex === virtualRow.index;
                const resolution = resolutionHistory[row.id];

                return (
                  <div
                    key={row.id}
                    onClick={() => {
                      playPseudoHaptic();
                      setSelectedIndex(virtualRow.index);
                      setInspectedRow(row);
                    }}
                    style={{
                      position: "absolute",
                      top: 0,
                      left: 0,
                      width: "100%",
                      height: `${virtualRow.size}px`,
                      transform: `translateY(${virtualRow.start}px)`,
                    }}
                    className={`grid grid-cols-12 gap-2 px-4 py-2.5 items-center cursor-pointer transition-colors duration-150 ${
                      isSelected
                        ? "bg-blue-900/30 border-l-4 border-l-blue-500"
                        : "hover:bg-terminal-elevated/60"
                    }`}
                  >
                    {/* Index */}
                    <div className="col-span-1 text-ink-muted type-caption-mono tabular-nums">
                      {virtualRow.index + 1}
                    </div>

                    {/* Entry & Carrier */}
                    <div className="col-span-2 min-w-0">
                      <div className="type-mono-data font-medium text-ink-primary truncate">{row.entryNumber}</div>
                      <div className="type-caption-mono text-ink-muted truncate">{row.carrier}</div>
                    </div>

                    {/* Corridor */}
                    <div className="col-span-2 type-body-dense text-ink-secondary truncate">
                      {row.corridor}
                    </div>

                    {/* Statutory Finding */}
                    <div className="col-span-3 min-w-0">
                      <div className="type-body-dense font-medium text-ink-primary truncate">
                        {row.discrepancyTitle}
                      </div>
                      <div className="statutory-cite text-[12px] text-ink-cobalt truncate">{row.statutoryCode}</div>
                    </div>

                    {/* Exposure */}
                    <div className="col-span-1 text-right type-mono-data font-medium text-ink-crimson">
                      <TabularAmount value={row.exposureAmount} />
                    </div>

                    {/* Confidence */}
                    <div className="col-span-1 text-center tabular-nums">
                      <span
                        className={`px-1.5 py-0.5 rounded type-caption-mono font-medium ${
                          row.confidence < 0.85
                            ? "bg-amber-500/10 text-ink-amber border border-amber-500/30"
                            : "bg-emerald-500/10 text-ink-emerald border border-emerald-500/30"
                        }`}
                      >
                        {Math.round(row.confidence * 100)}%
                      </span>
                    </div>

                    {/* Status & Action */}
                    <div className="col-span-2 flex items-center justify-center gap-1.5">
                      {resolution ? (
                        <span className="px-2 py-0.5 rounded type-caption-mono font-medium bg-emerald-500/20 text-emerald-300 border border-emerald-500/40">
                          RESOLVED
                        </span>
                      ) : (
                        <span
                          className={`px-2 py-0.5 rounded type-caption-mono font-medium ${
                            row.status === "QUARANTINED"
                              ? "bg-red-500/10 text-ink-crimson border border-red-500/30"
                              : "bg-slate-800 text-ink-secondary"
                          }`}
                        >
                          {row.status}
                        </span>
                      )}
                      <button
                        type="button"
                        onClick={(e) => {
                          e.stopPropagation();
                          playPseudoHaptic();
                          setInspectedRow(row);
                        }}
                        className="px-2 py-1 type-caption-mono bg-terminal-elevated hover:bg-cobalt-600 hover:text-canvas-stone text-ink-secondary rounded border border-terminal-border transition-colors"
                      >
                        Inspect
                      </button>
                    </div>
                  </div>
                );
              })}
            </div>
          )}
        </div>
          </div>
        </div>
      </div>

      {/* 4. DISCREPANCY INSPECTION DRAWER / MODAL */}
      {inspectedRow && (
        <div className="fixed inset-0 z-50 bg-canvas-dark/80 backdrop-blur-sm flex items-center justify-center p-4">
          <div className="bg-terminal-slate border border-terminal-subtle rounded-2xl w-full max-w-2xl p-6 shadow-2xl space-y-4 font-mono">
            <div className="flex items-center justify-between border-b border-terminal-subtle pb-3">
              <div>
                <span className="type-caption-mono uppercase text-ink-cobalt font-medium">
                  ENTRY INSPECTION
                </span>
                <h3 className="type-heading-sm text-ink-primary">{inspectedRow.entryNumber}</h3>
              </div>
              <button
                onClick={() => {
                  playPseudoHaptic();
                  setInspectedRow(null);
                }}
                className="p-1.5 text-ink-muted hover:text-ink-primary rounded-lg hover:bg-terminal-elevated"
              >
                <X className="w-5 h-5" />
              </button>
            </div>

            <div className="grid grid-cols-2 gap-3 type-mono-data">
              <div className="p-3 rounded-lg bg-canvas-dark border border-terminal-subtle">
                <div className="text-ink-muted type-caption-mono">CARRIER & CORRIDOR</div>
                <div className="font-medium text-ink-primary mt-0.5">{inspectedRow.carrier}</div>
                <div className="text-ink-muted type-caption-mono">{inspectedRow.corridor}</div>
              </div>

              <div className="p-3 rounded-lg bg-canvas-dark border border-terminal-subtle">
                <div className="text-ink-muted type-caption-mono">STATUTORY EXPOSURE</div>
                <div className="font-semibold text-ink-crimson text-base mt-0.5 tabular-nums">
                  <TabularAmount value={inspectedRow.exposureAmount} />
                </div>
                <div className="text-ink-muted type-caption-mono tabular-nums">
                  Confidence: {Math.round(inspectedRow.confidence * 100)}%
                </div>
              </div>
            </div>

            <div className="p-3 rounded-lg bg-canvas-dark border border-terminal-subtle type-mono-data space-y-1">
              <div className="statutory-cite text-ink-cobalt">{inspectedRow.statutoryCode}</div>
              <div className="font-medium text-ink-primary">{inspectedRow.discrepancyTitle}</div>
              <p className="type-body-dense text-ink-secondary font-sans">{inspectedRow.discrepancyDescription}</p>
            </div>

            {/* Provenance & Real Multi-Page PDF Link */}
            {inspectedRow.pdfFilename && (
              <div className="p-3 rounded-lg bg-blue-950/20 border border-blue-900/50 flex flex-col sm:flex-row sm:items-center justify-between gap-2 type-mono-data">
                <div>
                  <div className="type-caption-mono uppercase text-ink-cobalt font-medium">
                    DOCUMENT PROVENANCE
                  </div>
                  <div className="text-ink-primary font-medium mt-0.5">{inspectedRow.pdfFilename}</div>
                  {inspectedRow.ownershipPath && (
                    <div className="type-caption-mono text-ink-amber mt-1">
                      yente Graph: {inspectedRow.ownershipPath}
                    </div>
                  )}
                </div>
                <a
                  href={resolveAssetPath(`/nightmares/${inspectedRow.pdfFilename}`)}
                  target="_blank"
                  rel="noreferrer"
                  className="inline-flex items-center gap-1.5 px-3 py-1.5 bg-cobalt-600 hover:bg-cobalt-500 text-canvas-stone font-mono text-xs font-semibold rounded-md transition-colors shrink-0"
                >
                  <span>Open Archival PDF</span>
                  <ExternalLink className="w-3.5 h-3.5" />
                </a>
              </div>
            )}

            {/* Mounted ThreeWayResolutionBar */}
            <div className="pt-2">
              <ThreeWayResolutionBar
                discrepancyId={inspectedRow.id}
                confidence={inspectedRow.confidence}
                statutoryCode={inspectedRow.statutoryCode}
                onResolved={() => {
                  playPseudoHaptic();
                }}
              />
            </div>
          </div>
        </div>
      )}

      {/* 5. ⌘K COMMAND PALETTE MODAL */}
      {isCommandBarOpen && (
        <div className="fixed inset-0 z-50 bg-canvas-dark/80 backdrop-blur-md flex items-start justify-center pt-20 p-4">
          <div className="bg-terminal-slate border border-terminal-subtle rounded-xl w-full max-w-lg shadow-2xl overflow-hidden type-mono-data">
            <div className="p-3 border-b border-terminal-subtle flex items-center gap-2 bg-canvas-dark">
              <Command className="w-4 h-4 text-ink-cobalt" />
              <input
                type="text"
                autoFocus
                value={searchQuery}
                onChange={(e) => setSearchQuery(e.target.value)}
                placeholder="Type carrier name, corridor, statute, or entry number..."
                className="w-full bg-transparent border-none text-ink-primary focus:outline-none placeholder:text-ink-muted type-mono-data"
              />
              <button
                onClick={() => setIsCommandBarOpen(false)}
                className="text-ink-muted hover:text-ink-primary"
              >
                <X className="w-4 h-4" />
              </button>
            </div>

            <div className="p-2 max-h-72 overflow-y-auto space-y-1">
              <div className="px-2 py-1 type-caption-mono text-ink-muted uppercase font-medium">
                Filter by Queue Owner:
              </div>
              {[
                { id: "all", label: "Show All 500 Entries" },
                { id: "broker_desk", label: "Route to Broker Desk (GRI & 1592 Defense)" },
                { id: "ap_carrier_dispute", label: "Route to AP Carrier Dispute (OSRA 2022 & FMC)" },
                { id: "shipper_outreach", label: "Route to Shipper Outreach (152.103 Assists)" },
              ].map((opt) => (
                <button
                  key={opt.id}
                  onClick={() => {
                    playPseudoHaptic();
                    setActiveOwnerFilter(opt.id as OwnerRoute);
                    setIsCommandBarOpen(false);
                  }}
                  className="w-full text-left px-3 py-2 rounded-lg hover:bg-cobalt-600 hover:text-canvas-stone text-ink-secondary flex items-center justify-between"
                >
                  <span>{opt.label}</span>
                  <ChevronRight className="w-3.5 h-3.5 opacity-60" />
                </button>
              ))}
            </div>
          </div>
        </div>
      )}
    </div>
  );
};
