"use client";

import React from "react";
import { Briefcase, Cpu, Scale } from "lucide-react";
import { sound } from "@/lib/audio";

export type IcpPersona = "cfo" | "counsel" | "cto";

interface IcpPersonaSwitcherProps {
  persona: IcpPersona;
  onChange: (persona: IcpPersona) => void;
}

const LENSES: Array<{ id: IcpPersona; label: string; icon: React.ReactNode }> = [
  { id: "cfo", label: "Finance", icon: <Briefcase className="w-3.5 h-3.5" /> },
  { id: "counsel", label: "Counsel", icon: <Scale className="w-3.5 h-3.5" /> },
  { id: "cto", label: "Engineering", icon: <Cpu className="w-3.5 h-3.5" /> },
];

export const IcpPersonaSwitcher: React.FC<IcpPersonaSwitcherProps> = ({
  persona,
  onChange,
}) => {
  const handleSwitch = (newPersona: IcpPersona) => {
    sound.playTick();
    onChange(newPersona);
  };

  return (
    <div className="inline-flex flex-wrap items-center gap-1 p-1 bg-terminal-slate border border-terminal-subtle rounded-lg font-mono text-xs">
      <span className="text-[10px] text-ink-muted uppercase px-2 font-semibold hidden md:inline">
        View as
      </span>

      {LENSES.map((lens) => {
        const isActive = persona === lens.id;
        return (
          <button
            key={lens.id}
            onClick={() => handleSwitch(lens.id)}
            aria-pressed={isActive}
            className={`flex items-center gap-1.5 py-1.5 px-2.5 rounded-md font-semibold text-[11px] uppercase tracking-wider transition-colors duration-200 ${
              isActive
                ? "bg-cobalt-600 text-canvas-stone shadow-sm"
                : "text-ink-muted hover:text-ink-primary hover:bg-terminal-elevated"
            }`}
          >
            {lens.icon}
            <span>{lens.label}</span>
          </button>
        );
      })}
    </div>
  );
};
