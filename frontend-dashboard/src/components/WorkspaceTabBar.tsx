"use client";

import React from "react";
import { Download, Columns2, FileText, LayoutList } from "lucide-react";
import { sound } from "@/lib/audio";

export interface PillarTabItem {
  id: string;
  shortTag: string;
  icon: React.ReactNode;
}

interface WorkspaceTabBarProps {
  pillars: PillarTabItem[];
  activeConceptId: string;
  onSelectConcept: (id: string) => void;
  onExportAuditPacket: () => void;
  desktopViewMode: "split" | "doc_focus" | "report_focus";
  setDesktopViewMode: (mode: "split" | "doc_focus" | "report_focus") => void;
}

export const WorkspaceTabBar: React.FC<WorkspaceTabBarProps> = ({
  pillars,
  activeConceptId,
  onSelectConcept,
  onExportAuditPacket,
  desktopViewMode,
  setDesktopViewMode,
}) => {
  return (
    <div className="flex flex-col lg:flex-row lg:items-center justify-between gap-3 mb-4 pb-2 border-b border-terminal-subtle font-mono text-xs">
      <div className="flex items-center gap-2 overflow-x-auto max-w-full" role="tablist" aria-label="Compliance workbench pillars">
        <span className="text-[10px] text-slate-400 uppercase font-bold shrink-0">
          Workspace:
        </span>
        {pillars.map((pillar) => {
          const isActive = activeConceptId === pillar.id;
          return (
            <button
              key={pillar.id}
              role="tab"
              aria-selected={isActive}
              onClick={() => onSelectConcept(pillar.id)}
              className={`flex items-center gap-1.5 px-3 py-1.5 rounded-md border whitespace-nowrap transition-colors ${
                isActive
                  ? "bg-terminal-elevated border-cobalt-500 text-ink-primary shadow-sm ring-1 ring-cobalt-500/50"
                  : "bg-terminal-slate border-terminal-subtle text-ink-muted hover:text-ink-primary"
              }`}
            >
              {pillar.icon}
              <span>{pillar.shortTag}</span>
            </button>
          );
        })}
      </div>

      {/* Export Board & Counsel Audit Packet + Desktop 3-Way Layout Mode Switcher */}
      <div className="hidden lg:flex items-center gap-2 shrink-0">
        <button
          onClick={onExportAuditPacket}
          className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg bg-cobalt-600 hover:bg-cobalt-500 text-canvas-stone font-mono text-xs font-semibold uppercase tracking-wider transition-colors shadow-xs"
        >
          <Download className="w-3.5 h-3.5" />
          <span>Export Board &amp; Counsel Audit Packet</span>
        </button>
        <div className="flex items-center gap-1 p-0.5 bg-terminal-slate border border-terminal-subtle rounded-lg shrink-0">
          <button
            type="button"
            onClick={() => {
              sound.playTick();
              setDesktopViewMode("split");
            }}
            title="Split View (60/40)"
            className={`flex items-center gap-1 px-2.5 py-1 rounded type-caption-mono transition-colors ${
              desktopViewMode === "split"
                ? "bg-cobalt-600 text-canvas-stone font-medium shadow-xs"
                : "text-ink-muted hover:text-ink-primary"
            }`}
          >
            <Columns2 className="w-3 h-3" />
            <span>Split View</span>
          </button>
          <button
            type="button"
            onClick={() => {
              sound.playTick();
              setDesktopViewMode("doc_focus");
            }}
            title="Focus on Document"
            className={`flex items-center gap-1 px-2.5 py-1 rounded type-caption-mono transition-colors ${
              desktopViewMode === "doc_focus"
                ? "bg-cobalt-600 text-canvas-stone font-medium shadow-xs"
                : "text-ink-muted hover:text-ink-primary"
            }`}
          >
            <FileText className="w-3 h-3" />
            <span>Document Only</span>
          </button>
          <button
            type="button"
            onClick={() => {
              sound.playTick();
              setDesktopViewMode("report_focus");
            }}
            title="Focus on Forensic Report"
            className={`flex items-center gap-1 px-2.5 py-1 rounded type-caption-mono transition-colors ${
              desktopViewMode === "report_focus"
                ? "bg-cobalt-600 text-canvas-stone font-medium shadow-xs"
                : "text-ink-muted hover:text-ink-primary"
            }`}
          >
            <LayoutList className="w-3 h-3" />
            <span>Report Only</span>
          </button>
        </div>
      </div>
    </div>
  );
};
