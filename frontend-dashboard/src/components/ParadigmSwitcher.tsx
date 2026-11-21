"use client";

import React, { useEffect } from "react";
import { Layout, ListOrdered } from "lucide-react";
import { playPseudoHaptic } from "@/lib/firewall-core";

export type ParadigmId = "var-1" | "var-2";

interface ParadigmSwitcherProps {
  activeParadigm: ParadigmId;
  onChange: (paradigm: ParadigmId) => void;
  showLabel?: boolean;
}

const PARADIGMS: { id: ParadigmId; label: string; shortcut: string; icon: React.ReactNode }[] = [
  { id: "var-1", label: "Workbench", shortcut: "⌘1", icon: <Layout className="w-3.5 h-3.5" /> },
  { id: "var-2", label: "Triage Desk", shortcut: "⌘2", icon: <ListOrdered className="w-3.5 h-3.5" /> },
];

export const ParadigmSwitcher: React.FC<ParadigmSwitcherProps> = ({
  activeParadigm,
  onChange,
  showLabel = true,
}) => {
  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      if ((e.metaKey || e.ctrlKey) && !e.shiftKey && !e.altKey) {
        if (e.key === "1") {
          e.preventDefault();
          playPseudoHaptic();
          onChange("var-1");
        } else if (e.key === "2") {
          e.preventDefault();
          playPseudoHaptic();
          onChange("var-2");
        }
      }
    };

    window.addEventListener("keydown", handleKeyDown);
    return () => window.removeEventListener("keydown", handleKeyDown);
  }, [onChange]);

  return (
    <div className="flex items-center gap-1 p-1 rounded-xl bg-terminal-slate/90 border border-terminal-subtle backdrop-blur-md shadow-2xl">
      {showLabel && (
        <span className="text-[10px] font-mono text-slate-400 px-2 uppercase tracking-widest hidden md:inline-block">
          PARADIGM:
        </span>
      )}
      {PARADIGMS.map((p) => {
        const isActive = activeParadigm === p.id;
        return (
          <button
            key={p.id}
            onClick={() => { playPseudoHaptic(); onChange(p.id); }}
            className={`flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-mono transition-all duration-150 active:scale-[0.97] ${
              isActive
                ? "bg-blue-600 text-canvas-stone font-semibold shadow-sm border border-blue-400/40"
                : "text-slate-400 hover:text-slate-200 hover:bg-terminal-elevated/60"
            }`}
            title={`Switch to ${p.label} (${p.shortcut})`}
          >
            {p.icon}
            <span>{p.label}</span>
            <span
              className={`text-[9px] px-1 py-0.2 rounded border ml-0.5 ${
                isActive
                  ? "bg-blue-700/80 border-blue-400/40 text-blue-100"
                  : "bg-terminal-elevated border-terminal-border text-slate-400"
              }`}
            >
              {p.shortcut}
            </span>
          </button>
        );
      })}
    </div>
  );
};
