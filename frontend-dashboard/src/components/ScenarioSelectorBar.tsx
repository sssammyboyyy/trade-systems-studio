"use client";

import React from "react";
import { motion } from "framer-motion";
import { Compass, ShieldAlert, FileCheck2 } from "lucide-react";
import { MOCK_AUDIT_DATA } from "@/data/mockData";
import { formatUsd } from "@/lib/money";

export interface Scenario {
  id: string;
  name: string;
  route: string;
  concept_id: string;
  risk_type: string;
  statutory_code: string;
  default_exposure: string;
  severity: "critical" | "warning" | "opportunity";
}

const usd = (v: string | number) => formatUsd(v).replace(/\.00$/, "");

// The three bundled sample documents; amounts are the engine's results on each.
export const CORRIDOR_SCENARIOS: Scenario[] = [
  {
    id: "scenario_shenzhen_la_invoice",
    name: "Shenzhen to Los Angeles commercial invoice",
    route: "CN -> USLAX",
    concept_id: "concept_1_customs",
    risk_type: "Classification, CIF valuation and line arithmetic",
    statutory_code: "19 U.S.C. § 1592 / § 1401a",
    default_exposure: usd(MOCK_AUDIT_DATA.concept_1_customs.metrics.penalty_exposure_avoided),
    severity: "critical",
  },
  {
    id: "scenario_yantian_la_freight",
    name: "Yantian to Los Angeles ocean freight bill",
    route: "CNYTN -> USLAX",
    concept_id: "concept_2_freight",
    risk_type: "Fuel surcharge, chassis split and detention in free time",
    statutory_code: "Service contract / 46 CFR Part 541",
    default_exposure: usd(MOCK_AUDIT_DATA.concept_2_freight.metrics.carrier_overbilling_caught),
    severity: "critical",
  },
  {
    id: "scenario_la_rotterdam_drawback",
    name: "Los Angeles to Rotterdam re-export drawback",
    route: "USLAX -> NLRTM",
    concept_id: "concept_3_drawback",
    risk_type: "Unclaimed unused-merchandise drawback",
    statutory_code: "19 U.S.C. § 1313(j)",
    default_exposure: usd(MOCK_AUDIT_DATA.concept_3_drawback.metrics.drawback_unclaimed_unlocked),
    severity: "opportunity",
  },
];

interface ScenarioSelectorBarProps {
  activeScenarioId: string;
  onSelectScenario: (scenario: Scenario) => void;
}

export const ScenarioSelectorBar: React.FC<ScenarioSelectorBarProps> = ({
  activeScenarioId,
  onSelectScenario
}) => {
  return (
    <div className="w-full bg-terminal-slate border border-terminal-subtle rounded-xl p-3 mb-4 shadow-sm">
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-3">
        <div className="flex items-center gap-2">
          <Compass className="w-4 h-4 text-blue-500" />
          <span className="text-xs font-mono font-bold uppercase tracking-wider text-slate-300">
            Sample documents
          </span>
        </div>

        <div className="flex flex-wrap items-center gap-2">
          {CORRIDOR_SCENARIOS.map((sc) => {
            const isActive = sc.id === activeScenarioId;
            return (
              <motion.button
                key={sc.id}
                whileHover={{ scale: 1.02 }}
                whileTap={{ scale: 0.98 }}
                onClick={() => onSelectScenario(sc)}
                className={`flex items-center gap-2 px-3 py-1.5 rounded-lg text-xs font-mono transition-all border ${
                  isActive
                    ? "bg-blue-600/20 text-blue-400 border-blue-500/50 shadow-sm"
                    : "bg-terminal-elevated text-slate-300 hover:text-ink-primary border-terminal-border/60 hover:border-slate-500"
                }`}
              >
                {sc.severity === "critical" ? (
                  <ShieldAlert className="w-3.5 h-3.5 text-red-400" />
                ) : (
                  <FileCheck2 className="w-3.5 h-3.5 text-emerald-400" />
                )}
                <span className="font-semibold">{sc.name}</span>
                <span className="text-[10px] text-slate-400">({sc.route})</span>
                <span
                  className={`text-[10px] px-1.5 py-0.5 rounded font-mono font-bold ${
                    sc.severity === "critical"
                      ? "bg-red-500/10 text-red-400"
                      : "bg-emerald-500/10 text-emerald-400"
                  }`}
                >
                  {sc.default_exposure}
                </span>
              </motion.button>
            );
          })}
        </div>
      </div>
    </div>
  );
};
