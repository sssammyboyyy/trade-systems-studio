"use client";

import { AGGREGATE_METRICS } from "@/data/mockData";
import { formatUsd } from "@/lib/money";
import React, { useState, useEffect, useRef } from "react";
import { motion, AnimatePresence } from "framer-motion";
import { X, Play, Pause, ChevronLeft, ChevronRight, ExternalLink } from "lucide-react";
import { sound } from "@/lib/audio";
import { resolveAssetPath } from "@/lib/assets";

interface FilmTheaterModalProps {
  isOpen: boolean;
  onClose: () => void;
  onOpenLeadModal: () => void;
}

interface FilmScene {
  id: string;
  title: string;
  subtitle: string;
  duration: number;
  imageSrc: string;
  chapterBadge: string;
  conceptNumber: string;
  statutoryAnchor: string;
}

const FILM_SCENES: FilmScene[] = [
  {
    id: "scene-01",
    title: "Enterprise Importers Bleed Cash",
    subtitle: "Undetected Tariff Misclassifications & Unchecked Carrier Surcharges",
    duration: 5,
    imageSrc: "/film/frame-00-at-2.5s.png",
    chapterBadge: "THE FISCAL BLEED",
    conceptNumber: "00 / HOOK",
    statutoryAnchor: "$150,000+ per 100 entries",
  },
  {
    id: "scene-02",
    title: "Zero-Hallucination Trade Defense",
    subtitle: "Samuel's Deterministic Kernel: 100% Decimal Precision & Local Document Layout",
    duration: 5,
    imageSrc: "/film/frame-01-at-7.5s.png",
    chapterBadge: "THE ARCHITECTURE",
    conceptNumber: "01 / KERNEL",
    statutoryAnchor: "Zero Cloud API / < 200ms",
  },
  {
    id: "scene-03",
    title: "Customs Compliance Firewall",
    subtitle: "Cybernetic Document Laser Sweep & 19 U.S.C. § 1592 Penalty Mitigation",
    duration: 6,
    imageSrc: "/film/frame-02-at-13s.png",
    chapterBadge: "CUSTOMS DEFENSE",
    conceptNumber: "02 / 1592 FIREWALL",
    statutoryAnchor: `${formatUsd(AGGREGATE_METRICS.penalty_exposure_avoided)} penalty exposure flagged`,
  },
  {
    id: "scene-04",
    title: "Pre-Payment Freight Audit",
    subtitle: "Fuel surcharge, chassis split and detention inside free time (46 CFR Part 541)",
    duration: 5,
    imageSrc: "/film/frame-03-at-18.5s.png",
    chapterBadge: "FREIGHT INTERCEPT",
    conceptNumber: "03 / CARRIER OVERBILLING",
    statutoryAnchor: `${formatUsd(AGGREGATE_METRICS.carrier_overbilling_caught)} disputed`,
  },
  {
    id: "scene-05",
    title: "Duty Drawback Harvester",
    subtitle: "19 U.S.C. § 1313: Automated CBP 7501 to Outbound Export B/L Reconciliation",
    duration: 5,
    imageSrc: "/film/frame-04-at-23.5s.png",
    chapterBadge: "TREASURY YIELD",
    conceptNumber: "04 / DUTY DRAWBACK",
    statutoryAnchor: `${formatUsd(AGGREGATE_METRICS.drawback_unclaimed_unlocked)} drawback identified`,
  },
  {
    id: "scene-06",
    title: "Claim 25-Invoice Blind Audit",
    subtitle: "$0 Upfront Diagnostic Proof-of-Work Delivered by Samuel",
    duration: 4,
    imageSrc: "/film/frame-05-at-28s.png",
    chapterBadge: "EXECUTIVE PROPOSAL",
    conceptNumber: "05 / ADVISORY SPRINT",
    statutoryAnchor: "Confidential Verification",
  },
];

export const FilmTheaterModal: React.FC<FilmTheaterModalProps> = ({
  isOpen,
  onClose,
  onOpenLeadModal,
}) => {
  const [currentSceneIdx, setCurrentSceneIdx] = useState<number>(0);
  const [isPlaying, setIsPlaying] = useState<boolean>(true);
  const [progress, setProgress] = useState<number>(0);

  // Auto-play timer
  useEffect(() => {
    if (!isOpen || !isPlaying) return;

    const intervalMs = 100;
    const currentScene = FILM_SCENES[currentSceneIdx];
    const stepIncrement = (intervalMs / 1000 / currentScene.duration) * 100;

    const timer = setInterval(() => {
      setProgress((prev) => {
        if (prev + stepIncrement >= 100) {
          // Advance to next scene or loop
          setCurrentSceneIdx((curr) => (curr + 1) % FILM_SCENES.length);
          return 0;
        }
        return prev + stepIncrement;
      });
    }, intervalMs);

    return () => clearInterval(timer);
  }, [isOpen, isPlaying, currentSceneIdx]);

  const handleSelectScene = (index: number) => {
    sound.click();
    setCurrentSceneIdx(index);
    setProgress(0);
  };

  const togglePlay = () => {
    sound.click();
    setIsPlaying((prev) => !prev);
  };

  const handleNext = () => {
    sound.click();
    setCurrentSceneIdx((prev) => (prev + 1) % FILM_SCENES.length);
    setProgress(0);
  };

  const handlePrev = () => {
    sound.click();
    setCurrentSceneIdx((prev) => (prev - 1 + FILM_SCENES.length) % FILM_SCENES.length);
    setProgress(0);
  };

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

  if (!isOpen) return null;

  const activeScene = FILM_SCENES[currentSceneIdx];

  return (
    <AnimatePresence>
      <div
        role="dialog"
        aria-modal="true"
        aria-labelledby="film-theater-modal-title"
        className="fixed inset-0 z-50 flex items-center justify-center p-3 sm:p-6 bg-canvas-dark/85 backdrop-blur-xl"
      >
        <motion.div
          ref={modalRef}
          initial={{ opacity: 0, scale: 0.95, y: 20 }}
          animate={{ opacity: 1, scale: 1, y: 0 }}
          exit={{ opacity: 0, scale: 0.95, y: 20 }}
          transition={{ duration: 0.25, ease: "easeOut" }}
          className="relative w-full max-w-5xl bg-canvas-dark border border-slate-700/80 rounded-xl overflow-hidden shadow-2xl flex flex-col"
        >
          {/* Top Bar */}
          <div className="flex items-center justify-between px-5 py-3.5 border-b border-slate-800 bg-terminal-slate/90">
            <div className="flex items-center gap-3">
              <div className="w-7 h-7 rounded-sm bg-cobalt-950 border border-cobalt-800 text-cobalt-400 flex items-center justify-center font-mono font-bold text-xs">
                🎬
              </div>
              <div>
                <div className="flex items-center gap-2">
                  <span id="film-theater-modal-title" className="font-mono text-xs font-bold text-slate-100 uppercase tracking-wider">
                    KEYNOTE FILM TEASER
                  </span>
                  <span className="text-[10px] font-mono text-slate-400">•</span>
                  <span className="font-mono text-[11px] text-cobalt-400 font-semibold uppercase">
                    30s BROADCAST CUT
                  </span>
                </div>
              </div>
            </div>

            <div className="flex items-center gap-2">
              <button
                onClick={onClose}
                aria-label="Close dialog"
                className="p-1.5 text-slate-400 hover:text-ink-primary hover:bg-slate-800 rounded-sm transition-colors cursor-pointer"
                title="Close Theater"
              >
                <X className="w-5 h-5" />
              </button>
            </div>
          </div>

          {/* Film Screen Canvas / Snapshot Viewer */}
          <div className="relative aspect-video w-full bg-canvas-dark overflow-hidden flex items-center justify-center">
            {/* Active Scene Frame Snapshot */}
            <motion.img
              key={activeScene.id}
              initial={{ opacity: 0.4, scale: 1.02 }}
              animate={{ opacity: 1, scale: 1 }}
              transition={{ duration: 0.35 }}
              src={resolveAssetPath(activeScene.imageSrc)}
              alt={activeScene.title}
              className="w-full h-full object-contain"
            />

            {/* In-Frame Statutory Badge Overlay */}
            <div className="absolute top-4 left-4 z-10 flex items-center gap-2 pointer-events-none">
              <span className="px-2.5 py-1 bg-canvas-dark/75 backdrop-blur-md border border-slate-700 rounded-sm font-mono text-[11px] text-cobalt-400 font-bold uppercase tracking-wider">
                {activeScene.chapterBadge}
              </span>
              <span className="px-2 py-1 bg-canvas-dark/75 backdrop-blur-md border border-slate-800 rounded-sm font-mono text-[10px] text-slate-300">
                {activeScene.statutoryAnchor}
              </span>
            </div>

            {/* Quick Play/Pause Center Trigger Overlay on Hover */}
            <button
              onClick={togglePlay}
              className="absolute inset-0 w-full h-full opacity-0 hover:opacity-100 transition-opacity bg-canvas-dark/25 flex items-center justify-center"
            >
              <div className="w-16 h-16 rounded-full bg-cobalt-500/90 text-canvas-stone flex items-center justify-center shadow-lg transform hover:scale-110 transition-transform">
                {isPlaying ? <Pause className="w-8 h-8" /> : <Play className="w-8 h-8 ml-1" />}
              </div>
            </button>
          </div>

          {/* Timeline & Chapter Bar */}
          <div className="px-5 py-4 bg-terminal-slate border-t border-slate-800 flex flex-col gap-3">
            {/* Progress Scrubbing Bar */}
            <div className="w-full bg-slate-800 h-1.5 rounded-full overflow-hidden flex">
              {FILM_SCENES.map((scene, idx) => {
                const isActive = idx === currentSceneIdx;
                const isPast = idx < currentSceneIdx;
                return (
                  <div
                    key={scene.id}
                    onClick={() => handleSelectScene(idx)}
                    className="h-full cursor-pointer transition-all border-r border-slate-900/60 relative"
                    style={{ flex: scene.duration }}
                  >
                    <div
                      className={`h-full ${
                        isPast
                          ? "bg-cobalt-500"
                          : isActive
                          ? "bg-cobalt-400"
                          : "bg-transparent"
                      }`}
                      style={{
                        width: isActive ? `${progress}%` : isPast ? "100%" : "0%",
                      }}
                    />
                  </div>
                );
              })}
            </div>

            {/* Playback Controls & Chapter List */}
            <div className="flex flex-col sm:flex-row items-center justify-between gap-4">
              <div className="flex items-center gap-3">
                <button
                  onClick={handlePrev}
                  className="p-1.5 text-slate-300 hover:text-ink-primary hover:bg-slate-800 rounded-sm transition-colors"
                  title="Previous Chapter"
                >
                  <ChevronLeft className="w-5 h-5" />
                </button>

                <button
                  onClick={togglePlay}
                  className="p-2 bg-cobalt-600 hover:bg-cobalt-500 text-canvas-stone rounded-sm transition-colors shadow-sm"
                  title={isPlaying ? "Pause" : "Play"}
                >
                  {isPlaying ? <Pause className="w-4 h-4" /> : <Play className="w-4 h-4" />}
                </button>

                <button
                  onClick={handleNext}
                  className="p-1.5 text-slate-300 hover:text-ink-primary hover:bg-slate-800 rounded-sm transition-colors"
                  title="Next Chapter"
                >
                  <ChevronRight className="w-5 h-5" />
                </button>

                <div className="text-left ml-2">
                  <div className="font-mono text-xs font-bold text-slate-100 flex items-center gap-2">
                    <span>{activeScene.conceptNumber}</span>
                    <span className="text-slate-400">•</span>
                    <span className="text-cobalt-400 font-semibold">{activeScene.title}</span>
                  </div>
                  <div className="text-[11px] text-slate-400 hidden sm:block">
                    {activeScene.subtitle}
                  </div>
                </div>
              </div>

              {/* Call to Action Inside Player */}
              <div className="flex items-center gap-3 w-full sm:w-auto justify-end">
                <button
                  onClick={() => {
                    onClose();
                    onOpenLeadModal();
                  }}
                  className="px-4 py-2 bg-emerald-600 hover:bg-emerald-500 text-canvas-stone font-mono text-xs font-bold rounded-sm transition-all flex items-center gap-2 shadow-sm"
                >
                  <span>Request 25-Invoice Audit</span>
                  <ExternalLink className="w-3.5 h-3.5" />
                </button>
              </div>
            </div>
          </div>
        </motion.div>
      </div>
    </AnimatePresence>
  );
};
