"use client";

import React, { useState, useRef, useEffect } from "react";
import { Document, Page, pdfjs } from "react-pdf";
import { Discrepancy } from "@/lib/types";
import { DocumentScannerBeam } from "./DocumentScannerBeam";
import { sound } from "@/lib/audio";
import { resolveAssetPath } from "@/lib/assets";
import {
  ZoomIn,
  ZoomOut,
  RotateCcw,
  AlertTriangle,
  FileText,
  AlertCircle,
  ExternalLink,
  Scan,
  Shield,
} from "lucide-react";

// Configure pdfjs worker to local bundled worker
if (typeof window !== "undefined") {
  if (!pdfjs.GlobalWorkerOptions.workerSrc) {
    pdfjs.GlobalWorkerOptions.workerSrc = resolveAssetPath("/pdf.worker.min.mjs");
  }
}

interface PdfOverlayCanvasProps {
  documentUrl: string;
  filename: string;
  discrepancies: Discrepancy[];
  activeDiscrepancyId: string | null;
  onHoverDiscrepancy: (id: string | null) => void;
  onClickDiscrepancy: (id: string) => void;
}

export const PdfOverlayCanvas: React.FC<PdfOverlayCanvasProps> = ({
  documentUrl,
  filename,
  discrepancies,
  activeDiscrepancyId,
  onHoverDiscrepancy,
  onClickDiscrepancy,
}) => {
  const [scale, setScale] = useState<number>(1.0);
  const [numPages, setNumPages] = useState<number>(1);
  const [currentPage, setCurrentPage] = useState<number>(1);
  const [piiRedacted, setPiiRedacted] = useState<boolean>(false);
  const [pageAspectRatio, setPageAspectRatio] = useState<number>(792 / 612); // Standard letter ratio
  const [isLoading, setIsLoading] = useState<boolean>(true);
  const [hasError, setHasError] = useState<boolean>(false);
  const [isScanning, setIsScanning] = useState<boolean>(false);
  const [analyzingBlockId, setAnalyzingBlockId] = useState<string | null>(null);
  const [beaconDismissed, setBeaconDismissed] = useState<boolean>(false);
  const containerRef = useRef<HTMLDivElement>(null);

  // Base canvas dimensions in pixels (matches 612 x 792 letter aspect ratio)
  const baseWidth = 612;

  // Uploads arrive as blob: URLs; bundled fixtures are served from /public/nightmares
  // (byte-identical to the backend copies, so their SHA-256 matches the provenance bar).
  const pickUrl = (): string => {
    if (documentUrl && /^(blob:|https?:)/.test(documentUrl)) return documentUrl;
    if (documentUrl && documentUrl.startsWith("/nightmares/")) return resolveAssetPath(documentUrl);
    if (documentUrl && documentUrl.startsWith("/api/v1/documents/")) return resolveAssetPath(`/nightmares/${filename}`);
    return "";
  };
  const [resolvedUrl, setResolvedUrl] = useState<string>(pickUrl);

  useEffect(() => {
    setIsLoading(true);
    setHasError(false);
    setCurrentPage(1);
    const next = pickUrl();
    setResolvedUrl(next);
    if (!next) {
      setIsLoading(false);
      setHasError(true);
    }
    // Scanner sweep on document change
    setIsScanning(true);
    const scanTimer = setTimeout(() => setIsScanning(false), 2000);
    return () => clearTimeout(scanTimer);
    // pickUrl only reads filename and documentUrl, which are the dependencies
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [filename, documentUrl]);

  const triggerManualScan = () => {
    setIsScanning(false);
    setTimeout(() => setIsScanning(true), 50);
  };

  // Responsive scale initialization for mobile
  useEffect(() => {
    const handleResize = () => {
      if (typeof window !== "undefined") {
        if (window.innerWidth < 640) {
          setScale(0.58); // Fit mobile viewport width comfortably
        } else if (window.innerWidth < 1024) {
          setScale(0.85); // Fit tablet viewport
        } else {
          setScale(1.0); // Full desktop size
        }
      }
    };
    handleResize();
    window.addEventListener("resize", handleResize);
    return () => window.removeEventListener("resize", handleResize);
  }, []);

  // Zoom handlers
  const handleZoomIn = () => {
    sound.playTick();
    setScale((prev) => Math.min(prev + 0.15, 2.2));
  };
  const handleZoomOut = () => {
    sound.playTick();
    setScale((prev) => Math.max(prev - 0.15, 0.5));
  };
  const handleResetZoom = () => {
    sound.playTick();
    if (typeof window !== "undefined" && window.innerWidth < 640) {
      setScale(0.58);
    } else {
      setScale(1.0);
    }
  };

  const handleBlockClick = (id: string) => {
    setBeaconDismissed(true);
    setAnalyzingBlockId(id);
    sound.playReticleLock();
    // A whisper slower: 420ms weighted laser lock-on trajectory before triggering view transition
    setTimeout(() => {
      setAnalyzingBlockId(null);
      onClickDiscrepancy(id);
    }, 420);
  };

  // Auto-scroll to active bounding box when hovered or selected
  useEffect(() => {
    if (!activeDiscrepancyId) return;
    const activeBoxEl = document.getElementById(`bbox-${activeDiscrepancyId}`);
    if (activeBoxEl && containerRef.current) {
      activeBoxEl.scrollIntoView({ behavior: "smooth", block: "center" });
    }
  }, [activeDiscrepancyId]);

  const onDocumentLoadSuccess = ({ numPages }: { numPages: number }) => {
    setNumPages(numPages);
    setIsLoading(false);
    setHasError(false);
  };

  const onDocumentLoadError = (err: Error) => {
    console.warn("PDF could not be loaded:", err);
    setIsLoading(false);
    setHasError(true);
  };

  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  const onPageLoadSuccess = (page: any) => {
    if (page && page.width && page.height) {
      setPageAspectRatio(page.height / page.width);
    }
    setIsLoading(false);
  };

  const renderedWidth = baseWidth * scale;
  const renderedHeight = renderedWidth * pageAspectRatio;
  // Canvas-relative annotation scaling locked to PDF zoom factor
  const overlayBadgeFontSize = `${Math.max(10, Math.round(11 * scale))}px`;
  const overlaySubFontSize = `${Math.max(9, Math.round(9.5 * scale))}px`;

  return (
    <div className="flex flex-col h-full bg-slate-100 dark:bg-canvas-dark border border-slate-200 dark:border-terminal-subtle overflow-hidden">
      {/* Canvas Top Toolbar */}
      <div className="flex items-center justify-between px-3 sm:px-4 py-2 bg-canvas-stone dark:bg-terminal-slate border-b border-slate-200 dark:border-terminal-subtle shrink-0 gap-2">
        <div className="flex items-center gap-2 truncate">
          <FileText className="w-4 h-4 text-cobalt-600 dark:text-ink-cobalt shrink-0" />
          <span className="type-mono-data text-slate-800 dark:text-ink-primary truncate">
            {filename}
          </span>
          <div className="flex items-center gap-1 bg-slate-100 dark:bg-canvas-dark/80 border border-slate-300 dark:border-terminal-subtle px-1.5 py-0.5 rounded-xs shrink-0 type-caption-mono">
            <button
              onClick={() => {
                sound.playTick();
                setCurrentPage((p) => Math.max(1, p - 1));
              }}
              disabled={currentPage <= 1}
              aria-label="Previous Page"
              className="px-1 text-slate-600 dark:text-ink-muted hover:text-slate-900 dark:hover:text-ink-primary disabled:opacity-30 disabled:cursor-not-allowed font-medium"
              title="Previous Page"
            >
              &lt;
            </button>
            <span className="text-slate-700 dark:text-ink-secondary font-medium px-0.5 tabular-nums">
              Page {currentPage} / {numPages}
            </span>
            <button
              onClick={() => {
                sound.playTick();
                setCurrentPage((p) => Math.min(numPages, p + 1));
              }}
              disabled={currentPage >= numPages}
              aria-label="Next Page"
              className="px-1 text-slate-600 dark:text-ink-muted hover:text-slate-900 dark:hover:text-ink-primary disabled:opacity-30 disabled:cursor-not-allowed font-medium"
              title="Next Page"
            >
              &gt;
            </button>
          </div>
        </div>

        {/* Viewport Zoom Controls, PII Redaction, & Laser Scan */}
        <div className="flex items-center gap-1 sm:gap-1.5 shrink-0">
          <button
            onClick={() => {
              sound.playTick();
              setPiiRedacted((r) => !r);
            }}
            aria-label={piiRedacted ? "Disable PII Redaction Mask" : "Redact Shipper and Consignee PII on Document"}
            aria-pressed={piiRedacted}
            title={piiRedacted ? "Disable PII Redaction Mask" : "Redact Shipper & Consignee PII on Document"}
            className={`flex items-center gap-1 px-2 py-1 rounded-sm font-mono text-[10px] uppercase font-bold transition-all border shadow-xs ${
              piiRedacted
                ? "bg-amber-500/20 text-amber-300 border-amber-500/60"
                : "bg-slate-100 dark:bg-terminal-elevated hover:bg-slate-200 dark:hover:bg-slate-800 text-slate-600 dark:text-slate-300 border-slate-300 dark:border-terminal-subtle"
            }`}
          >
            <Shield className="w-3 h-3 text-amber-400" />
            <span className="hidden sm:inline">{piiRedacted ? "PII Masked" : "Redact PII"}</span>
          </button>

          <button
            onClick={triggerManualScan}
            aria-label="Trigger Scanner Beam"
            title="Trigger Cybernetic Scanner Beam"
            className="flex items-center gap-1 px-2 py-1 bg-cobalt-50 dark:bg-cobalt-950/80 hover:bg-cobalt-100 dark:hover:bg-cobalt-900/60 text-cobalt-700 dark:text-cobalt-300 border border-cobalt-300 dark:border-cobalt-800 rounded-sm font-mono text-[10px] uppercase font-bold transition-all shadow-xs"
          >
            <Scan className="w-3 h-3 text-cobalt-600 dark:text-cobalt-400" />
            <span className="hidden md:inline">Laser Scan</span>
          </button>

          <button
            onClick={handleZoomOut}
            aria-label="Zoom Out"
            title="Zoom Out"
            className="p-1.5 hover:bg-slate-100 dark:hover:bg-terminal-elevated text-slate-600 dark:text-slate-400 hover:text-slate-900 dark:hover:text-slate-100 transition-colors border border-slate-300 dark:border-terminal-subtle rounded-sm"
          >
            <ZoomOut className="w-3.5 h-3.5" />
          </button>
          <span className="type-mono-data text-slate-700 dark:text-ink-numeric w-10 sm:w-12 text-center tabular-nums">
            {Math.round(scale * 100)}%
          </span>
          <button
            onClick={handleZoomIn}
            aria-label="Zoom In"
            title="Zoom In"
            className="p-1.5 hover:bg-slate-100 dark:hover:bg-terminal-elevated text-slate-600 dark:text-slate-400 hover:text-slate-900 dark:hover:text-slate-100 transition-colors border border-slate-300 dark:border-terminal-subtle rounded-sm"
          >
            <ZoomIn className="w-3.5 h-3.5" />
          </button>
          <button
            onClick={handleResetZoom}
            aria-label="Fit Scale"
            title="Fit Scale"
            className="p-1.5 hover:bg-slate-100 dark:hover:bg-terminal-elevated text-slate-600 dark:text-slate-400 hover:text-slate-900 dark:hover:text-slate-100 transition-colors border border-slate-300 dark:border-terminal-subtle rounded-sm"
          >
            <RotateCcw className="w-3.5 h-3.5" />
          </button>
        </div>
      </div>

      {/* Interactive Document Lens Guidance Strip */}
      <div className="flex items-center justify-between px-3 sm:px-4 py-1.5 bg-canvas-dark border-b border-terminal-subtle text-[11px] font-mono shrink-0">
        <div className="flex items-center gap-1.5 text-slate-300">
          <span className="inline-block w-2 h-2 rounded-full bg-emerald-400 animate-pulse" />
          <span className="font-semibold text-slate-200">Interactive Document Lens:</span>
          <span className="text-slate-400 hidden sm:inline">
            Click any highlighted block to trigger legal analysis and open statutory findings.
          </span>
          <span className="text-slate-400 sm:hidden">
            Tap any box to reveal statutory findings.
          </span>
        </div>
        <div className="text-[10px] text-slate-400 font-bold shrink-0">
          {discrepancies.length} VIOLATIONS FLAGGED
        </div>
      </div>

      {/* Viewport Scroll Canvas */}
      <div
        ref={containerRef}
        className="flex-1 overflow-auto p-3 sm:p-6 flex justify-center items-start rectilinear-grid relative bg-slate-200/50 dark:bg-canvas-dark"
      >
        {isLoading && (
          <div className="absolute top-0 left-0 right-0 h-0.5 bg-slate-300 dark:bg-slate-800 overflow-hidden z-40">
            <div className="h-full bg-cobalt-500 animate-pulse w-1/3" />
          </div>
        )}

        {hasError ? (
          <div className="flex flex-col items-center justify-center p-6 sm:p-8 bg-white dark:bg-terminal-slate border border-red-400 dark:border-red-900/40 max-w-md text-center my-auto rounded-sm shadow-sm">
            <AlertCircle className="w-10 h-10 text-red-500 mb-3" />
            <h4 className="text-sm font-bold font-mono text-slate-900 dark:text-slate-100 mb-1">
              Document Stream Notice
            </h4>
            <p className="text-xs text-slate-600 dark:text-slate-400 mb-4">
              Unable to load PDF stream directly into Web Worker. Open the raw document below to review:
            </p>
            <a
              href={resolveAssetPath(`/nightmares/${filename}`)}
              target="_blank"
              rel="noreferrer"
              className="flex items-center gap-2 px-4 py-2 bg-slate-900 dark:bg-terminal-elevated hover:bg-slate-800 type-mono-data text-canvas-stone border border-slate-700 transition-colors rounded-sm"
            >
              <span>Inspect Raw Document</span>
              <ExternalLink className="w-3.5 h-3.5" />
            </a>
          </div>
        ) : (
          <div
            style={{
              width: `${renderedWidth}px`,
              height: `${renderedHeight}px`,
              position: "relative",
              transition: "width 0.1s ease-out, height 0.1s ease-out",
            }}
            className="lens-surface-light shadow-xl shadow-slate-400/20 dark:shadow-2xl bg-canvas-stone text-ink-primary border border-slate-300 dark:border-slate-700 select-none shrink-0 rounded-xs overflow-hidden"
          >
            {/* Cybernetic Animated Laser Scanning Beam */}
            <DocumentScannerBeam
              isScanning={isScanning}
              onScanComplete={() => setIsScanning(false)}
            />

            {/* React-PDF Canvas Document Layer */}
            <Document
              file={resolvedUrl}
              onLoadSuccess={onDocumentLoadSuccess}
              onLoadError={onDocumentLoadError}
              loading=""
              className="w-full h-full overflow-hidden"
            >
              <Page
                pageNumber={currentPage}
                width={renderedWidth}
                renderTextLayer={false}
                renderAnnotationLayer={false}
                onLoadSuccess={onPageLoadSuccess}
                className="w-full h-full"
              />
            </Document>

            {/* Dynamic Viewport Bounding-Box Overlay Layer */}
            <div className="absolute inset-0 pointer-events-auto">
              {/* PII Redaction Masks when toggled */}
              {piiRedacted && (
                <>
                  <div
                    style={{
                      left: `${(50 / 1000) * renderedWidth}px`,
                      top: `${(65 / 1000) * renderedHeight}px`,
                      width: `${(210 / 1000) * renderedWidth}px`,
                      height: `${(28 / 1000) * renderedHeight}px`,
                      position: "absolute",
                      fontSize: overlaySubFontSize,
                    }}
                    className="bg-canvas-dark border border-amber-500/80 z-30 flex items-center justify-center font-mono text-amber-400 font-medium tracking-wider select-none shadow-sm"
                  >
                    [PII REDACTED]
                  </div>
                  <div
                    style={{
                      left: `${(320 / 1000) * renderedWidth}px`,
                      top: `${(105 / 1000) * renderedHeight}px`,
                      width: `${(220 / 1000) * renderedWidth}px`,
                      height: `${(26 / 1000) * renderedHeight}px`,
                      position: "absolute",
                      fontSize: overlaySubFontSize,
                    }}
                    className="bg-canvas-dark border border-amber-500/80 z-30 flex items-center justify-center font-mono text-amber-400 font-medium tracking-wider select-none shadow-sm"
                  >
                    [EIN / TAX ID MASKED]
                  </div>
                </>
              )}

              {discrepancies
                .filter((disc) => (disc.bounding_box.page_number || 1) === currentPage)
                .map((disc, index) => {
                const bbox = disc.bounding_box;
                // Normalized coordinates [0, 1000) mapped dynamically to viewport pixels
                const left = (bbox.x / 1000) * renderedWidth;
                const top = (bbox.y / 1000) * renderedHeight;
                const width = (bbox.width / 1000) * renderedWidth;
                const height = (bbox.height / 1000) * renderedHeight;

                const isSelected = activeDiscrepancyId === disc.id;
                const isAnalyzing = analyzingBlockId === disc.id;
                const isUncertain = disc.confidence < 0.85;

                // Color schemes based on severity for Light & Dark
                let borderColor = "border-red-600 dark:border-red-500";
                let bgColor = isSelected ? "bg-red-500/25" : "bg-red-500/12";
                let badgeBg = "bg-red-600 text-canvas-stone dark:bg-red-600 dark:text-canvas-stone";

                if (disc.severity === "opportunity") {
                  borderColor = "border-emerald-600 dark:border-emerald-500";
                  bgColor = isSelected ? "bg-emerald-500/25" : "bg-emerald-500/12";
                  badgeBg = "bg-emerald-600 text-canvas-stone dark:bg-emerald-600 dark:text-canvas-stone";
                } else if (disc.severity === "warning" || isUncertain) {
                  borderColor = "border-amber-600 dark:border-amber-500";
                  bgColor = isSelected ? "bg-amber-500/25" : "bg-amber-500/12";
                  badgeBg = "bg-amber-600 text-canvas-stone dark:bg-amber-600 dark:text-canvas-stone";
                }

                return (
                  <div
                    key={disc.id}
                    id={`bbox-${disc.id}`}
                    role="button"
                    tabIndex={0}
                    aria-label={`Inspect finding: ${disc.title}`}
                    onKeyDown={(e) => {
                      if (e.key === "Enter" || e.key === " ") {
                        e.preventDefault();
                        handleBlockClick(disc.id);
                      }
                    }}
                    onMouseEnter={() => {
                      sound.playTick();
                      onHoverDiscrepancy(disc.id);
                    }}
                    onMouseLeave={() => onHoverDiscrepancy(null)}
                    onClick={() => handleBlockClick(disc.id)}
                    style={{
                      left: `${left}px`,
                      top: `${top}px`,
                      width: `${width}px`,
                      height: `${height}px`,
                      position: "absolute",
                    }}
                    className={`cursor-pointer transition-all duration-300 ease-[cubic-bezier(0.16,1,0.3,1)] border-2 ${borderColor} ${bgColor} ${
                      isUncertain ? "border-dashed" : "border-solid"
                    } ${
                      isAnalyzing
                        ? "ring-4 ring-cyan-400 bg-cyan-500/30 shadow-[0_0_28px_rgba(56,189,248,0.5)] z-40 scale-[1.03]"
                        : isSelected
                        ? "ring-2 ring-cobalt-500 dark:ring-cobalt-400 z-30"
                        : "z-20 hover:shadow-md"
                    }`}
                  >
                    {/* Precision Mechanical Reticle Corners */}
                    <span className="absolute -top-[3px] -left-[3px] w-2 h-2 border-t-2 border-l-2 border-current pointer-events-none opacity-80" />
                    <span className="absolute -top-[3px] -right-[3px] w-2 h-2 border-t-2 border-r-2 border-current pointer-events-none opacity-80" />
                    <span className="absolute -bottom-[3px] -left-[3px] w-2 h-2 border-b-2 border-l-2 border-current pointer-events-none opacity-80" />
                    <span className="absolute -bottom-[3px] -right-[3px] w-2 h-2 border-b-2 border-r-2 border-current pointer-events-none opacity-80" />

                    {/* Auto-Pulse Radar Beacon for First-Time Visitor Guidance */}
                    {index === 0 && !beaconDismissed && (
                      <div className="absolute left-full top-1/2 -translate-y-1/2 ml-9 z-40 pointer-events-none flex items-center gap-1.5">
                        <span className="relative flex h-3 w-3">
                          <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-cyan-400 opacity-75"></span>
                          <span className="relative inline-flex rounded-full h-3 w-3 bg-cyan-500 shadow-sm shadow-cyan-500/50"></span>
                        </span>
                        <span className="px-2 py-0.5 bg-cyan-950/90 text-cyan-300 border border-cyan-400/80 rounded-full font-mono text-[9px] font-bold tracking-wider shadow-lg animate-pulse whitespace-nowrap">
                          TAP TO INSPECT
                        </span>
                      </div>
                    )}

                    {/* Active Laser Analysis Sweep Flare inside Block on Click */}
                    {isAnalyzing && (
                      <div className="absolute inset-0 bg-cyan-400/20 overflow-hidden pointer-events-none z-30 flex items-center">
                        <div className="w-full h-1 bg-gradient-to-r from-transparent via-cyan-300 to-transparent shadow-[0_0_12px_#38bdf8] animate-pulse" />
                      </div>
                    )}

                    {/* Numbered pin in the page margin: never covers document text */}
                    <span
                      aria-hidden
                      style={{ fontSize: overlaySubFontSize }}
                      className={`absolute right-0 top-1/2 -translate-y-1/2 translate-x-[calc(100%+6px)] flex h-[1.9em] w-[1.9em] items-center justify-center rounded-full font-mono font-bold tabular-nums shadow-sm ${badgeBg}`}
                    >
                      {index + 1}
                    </span>

                    {/* Full citation only for the selected finding, placed below the row */}
                    {isSelected && (
                      <div
                        style={{ fontSize: overlayBadgeFontSize, lineHeight: 1.25 }}
                        className={`absolute left-0 top-full mt-1 z-40 flex items-center gap-1 whitespace-nowrap rounded-xs px-1.5 py-0.5 font-mono font-medium tabular-nums shadow-md ${badgeBg}`}
                      >
                        {isUncertain && <AlertTriangle className="w-2.5 h-2.5" />}
                        <span>{disc.statutory_code}</span>
                        <span>·</span>
                        <span>{(disc.confidence * 100).toFixed(0)}%</span>
                      </div>
                    )}
                  </div>
                );
              })}
            </div>
          </div>
        )}
      </div>
    </div>
  );
};
