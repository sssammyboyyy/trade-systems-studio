"use client";

import React, { useState, useEffect, useRef } from "react";
import { AuditResult, KillShotMetrics } from "@/lib/types";
import { fetchAudit, fetchAggregateMetrics, uploadAndAuditDocument } from "@/lib/api";
import dynamic from "next/dynamic";
import { LeadCaptureModal } from "./LeadCaptureModal";
import { PenaltyExposureLadder } from "./PenaltyExposureLadder";
import { ExecutiveDossierModal } from "./ExecutiveDossierModal";
import { FilmTheaterModal } from "./FilmTheaterModal";
import { SanctionsGraphViewer } from "./SanctionsGraphViewer";
import { HtsClassifierViewer } from "./HtsClassifierViewer";
import { CustomsValuationViewer } from "./CustomsValuationViewer";
import { SystemArchitectureModal } from "./SystemArchitectureModal";
import { ExecutiveTourOverlay } from "./ExecutiveTourOverlay";
import { ScenarioSelectorBar, CORRIDOR_SCENARIOS, Scenario } from "./ScenarioSelectorBar";
import { InlineArchitectureFlow } from "./InlineArchitectureFlow";
import { ArchitectThesis } from "./ArchitectThesis";
import { IcpPersona } from "./IcpPersonaSwitcher";
import { ProvenanceMetadataBar } from "./ProvenanceCockpit";
import { MobileBottomNavPill } from "./MobileBottomNavPill";
import { WorkbenchHeader } from "./WorkbenchHeader";
import { SystemsHeroSection } from "./SystemsHeroSection";
import { KillShotMetricsBar } from "./KillShotMetricsBar";
import { AuditTerminalBay } from "./AuditTerminalBay";
import { WorkbenchFooter } from "./WorkbenchFooter";
import { WorkspaceTabBar } from "./WorkspaceTabBar";
import { sound } from "@/lib/audio";
import { recordTelemetry } from "@/lib/supabase";

import { INITIAL_CUSTOMS_NIGHTMARE_FIXTURE, AGGREGATE_METRICS } from "@/data/mockData";
import { DataSourceBanner } from "./DataSourceBanner";
import { ParadigmSwitcher, ParadigmId } from "./ParadigmSwitcher";
import { Var2TriageQueue } from "./variations/Var2TriageQueue";
import { FirewallProvider, usePreIngestFirewall, playPseudoHaptic } from "@/lib/firewall-core";
import { Scale, DollarSign, FileCheck2, Network, Binary, Landmark } from "lucide-react";

const PdfOverlayCanvas = dynamic(
  () => import("./PdfOverlayCanvas").then((mod) => mod.PdfOverlayCanvas),
  {
    ssr: false,
    loading: () => (
      <div className="flex flex-col items-center justify-center h-full bg-canvas-dark border border-terminal-subtle text-slate-400 font-mono text-xs gap-3">
        <div className="w-6 h-6 border-2 border-blue-500 border-t-transparent animate-spin rounded-full" />
        <span>Initializing High-Precision Document Lens...</span>
      </div>
    ),
  }
);

const ALL_PILLARS = [
  {
    id: "concept_1_customs",
    name: "01 / Customs Valuation & 1592 Defense",
    shortTag: "CUSTOMS FIREWALL",
    icon: <Scale className="w-3.5 h-3.5" />,
    statute: "19 U.S.C. § 1592 & 19 CFR § 152.103",
  },
  {
    id: "concept_2_freight",
    name: "02 / Pre-Payment Freight Overbilling",
    shortTag: "FREIGHT AUDIT",
    icon: <DollarSign className="w-3.5 h-3.5" />,
    statute: "46 CFR 545.5 & 46 CFR Part 541",
  },
  {
    id: "concept_3_drawback",
    name: "03 / Section 1313 Duty Drawback",
    shortTag: "DUTY DRAWBACK",
    icon: <FileCheck2 className="w-3.5 h-3.5" />,
    statute: "19 U.S.C. § 1313 Unused Merchandise",
  },
  {
    id: "concept_4_sanctions",
    name: "04 / Sanctions & Entity Graph",
    shortTag: "OFAC 50% GRAPH",
    icon: <Network className="w-3.5 h-3.5" />,
    statute: "31 CFR § 501 / OFAC 50% Rule",
  },
  {
    id: "concept_5_hts",
    name: "05 / HTS Classification Copilot",
    shortTag: "GRI 1-6 COPILOT",
    icon: <Binary className="w-3.5 h-3.5" />,
    statute: "WCO GRI 1 to 6 & 19 CFR § 24.23",
  },
  {
    id: "concept_6_valuation",
    name: "06 / CBP Assist & Valuation Register",
    shortTag: "152.103 ASSISTS",
    icon: <Landmark className="w-3.5 h-3.5" />,
    statute: "19 CFR § 152.103 & 19 CFR § 162.74",
  },
];

const DualPaneAuditViewerInner: React.FC = () => {
  const { exportAuditPacket, adoptAudit } = usePreIngestFirewall();
  const [uploadError, setUploadError] = useState<string | null>(null);
  const [activeParadigm, setActiveParadigm] = useState<ParadigmId>("var-1");
  const [activeConceptId, setActiveConceptId] = useState<string>("concept_1_customs");
  const [auditData, setAuditData] = useState<AuditResult>(INITIAL_CUSTOMS_NIGHTMARE_FIXTURE);
  const [aggregateMetrics, setAggregateMetrics] = useState<KillShotMetrics | null>(null);
  const [activeDiscrepancyId, setActiveDiscrepancyId] = useState<string | null>(null);
  const [isLoading, setIsLoading] = useState<boolean>(true);

  // Right-hand terminal tab state
  const [rightTerminalTab, setRightTerminalTab] = useState<"discrepancies" | "cargowise" | "developer_api">("discrepancies");

  // Executive lens: reframes the value proposition per evaluator
  const [persona, setPersona] = useState<IcpPersona>("counsel");

  // Modals & Guided Experience
  const [isModalOpen, setIsModalOpen] = useState<boolean>(false);
  const [isDossierOpen, setIsDossierOpen] = useState<boolean>(false);
  const [isFilmOpen, setIsFilmOpen] = useState<boolean>(false);
  const [isArchitectureModalOpen, setIsArchitectureModalOpen] = useState<boolean>(false);
  const [architectureModalTab, setArchitectureModalTab] = useState<"architecture" | "tests" | "math_proof" | "candidate" | "playground">("architecture");
  const [isTourActive, setIsTourActive] = useState<boolean>(false);

  // Mobile segmented view state ('doc' | 'findings') - Default to 'doc' so source document is visible first
  const [mobileTab, setMobileTab] = useState<"findings" | "doc">("doc");
  // Desktop layout view mode ('split' | 'doc_focus' | 'report_focus')
  const [desktopViewMode, setDesktopViewMode] = useState<"split" | "doc_focus" | "report_focus">("split");
  const [isMobileNavOpen, setIsMobileNavOpen] = useState<boolean>(false);
  const [isPillInViewport, setIsPillInViewport] = useState<boolean>(false);
  const [isMobileViewport, setIsMobileViewport] = useState<boolean>(false);
  const fileInputRef = useRef<HTMLInputElement>(null);
  const workbenchContainerRef = useRef<HTMLDivElement>(null);

  const handleCustomFileUpload = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (!file) return;

    sound.playLock();
    setIsLoading(true);
    setUploadError(null);
    try {
      const result = await uploadAndAuditDocument(file);
      setAuditData(result);
      setActiveConceptId("client_upload_audit");
      setActiveDiscrepancyId(result.discrepancies[0]?.id || null);
      recordTelemetry({
        event_type: "client_pdf_upload_audited",
        metadata: {
          filename: file.name,
          size: file.size,
          discrepancies_count: result.discrepancies.length,
        },
      });
    } catch (err) {
      setUploadError(err instanceof Error ? err.message : "The document could not be audited.");
    } finally {
      setIsLoading(false);
      if (fileInputRef.current) fileInputRef.current.value = "";
    }
  };

  // Decisions and the audit packet always refer to the audit on screen.
  useEffect(() => {
    if (auditData) adoptAudit(auditData);
  }, [auditData, adoptAudit]);

  const switchConcept = (conceptId: string) => {
    sound.playLock();
    setActiveConceptId(conceptId);
    if (typeof window !== "undefined") {
      const slugMap: Record<string, string> = {
        concept_1_customs: "customs",
        concept_2_freight: "freight",
        concept_3_drawback: "drawback",
        concept_4_sanctions: "sanctions",
        concept_5_hts: "hts",
        concept_6_valuation: "valuation",
        concept_clean_fob: "clean_fob",
        client_upload_audit: "upload",
      };
      const slug = slugMap[conceptId] || conceptId;
      window.history.replaceState(null, "", `#${slug}`);
    }
  };

  const handleParadigmChange = (p: ParadigmId) => {
    setActiveParadigm(p);
    if (typeof window !== "undefined") {
      window.history.replaceState(null, "", `#${p}`);
    }
  };

  useEffect(() => {
    if (typeof window !== "undefined") {
      const hash = window.location.hash.toLowerCase().replace("#", "");
      const params = new URLSearchParams(window.location.search);
      const tabParam = params.get("tab") || hash;

      if (hash === "arc" || hash === "wiretap") {
        setArchitectureModalTab("architecture");
        setIsArchitectureModalOpen(true);
      } else if (hash === "var-2" || hash === "triage") {
        setActiveParadigm("var-2");
      } else if (hash === "var-1" || hash === "workbench" || hash === "customs") {
        setActiveParadigm("var-1");
        setActiveConceptId("concept_1_customs");
      }

      if (tabParam === "sanctions" || tabParam === "concept_4_sanctions") {
        setActiveConceptId("concept_4_sanctions");
      } else if (tabParam === "hts" || tabParam === "concept_5_hts") {
        setActiveConceptId("concept_5_hts");
      } else if (tabParam === "valuation" || tabParam === "concept_6_valuation") {
        setActiveConceptId("concept_6_valuation");
      } else if (tabParam === "freight" || tabParam === "concept_2_freight") {
        setActiveConceptId("concept_2_freight");
      } else if (tabParam === "drawback" || tabParam === "concept_3_drawback") {
        setActiveConceptId("concept_3_drawback");
      } else if (tabParam === "clean_fob" || tabParam === "concept_clean_fob") {
        setActiveConceptId("concept_clean_fob");
      } else if (tabParam === "architecture" || tabParam === "tests" || tabParam === "playground" || tabParam === "api") {
        if (tabParam === "tests") {
          setArchitectureModalTab("tests");
        } else if (tabParam === "playground" || tabParam === "api") {
          setArchitectureModalTab("playground");
        } else {
          setArchitectureModalTab("architecture");
        }
        setIsArchitectureModalOpen(true);
      } else if (tabParam === "dossier") {
        setIsDossierOpen(true);
      } else if (tabParam === "film" || tabParam === "keynote") {
        setIsFilmOpen(true);
      } else if (tabParam === "tour" || tabParam === "walkthrough") {
        setIsTourActive(true);
      }

      const handleHashChange = () => {
        const h = window.location.hash.toLowerCase().replace("#", "");
        if (h === "arc" || h === "wiretap") {
          setArchitectureModalTab("architecture");
          setIsArchitectureModalOpen(true);
        } else if (h === "var-2" || h === "triage") {
          setActiveParadigm("var-2");
        } else if (h === "var-1" || h === "workbench" || h === "customs") {
          setActiveParadigm("var-1");
          setActiveConceptId("concept_1_customs");
        }
      };

      window.addEventListener("hashchange", handleHashChange);
      return () => window.removeEventListener("hashchange", handleHashChange);
    }
  }, []);

  // Track responsive viewport width for contextual floating pill
  useEffect(() => {
    if (typeof window === "undefined") return;
    const handleResize = () => {
      setIsMobileViewport(window.innerWidth < 1024);
    };
    handleResize();
    window.addEventListener("resize", handleResize);
    return () => window.removeEventListener("resize", handleResize);
  }, []);

  // Contextual scroll intersection: floating pill only shows when workbench is actively in view
  useEffect(() => {
    const el = workbenchContainerRef.current;
    if (!el || typeof window === "undefined" || !("IntersectionObserver" in window)) {
      return;
    }

    const observer = new IntersectionObserver(
      ([entry]) => {
        setIsPillInViewport(entry.isIntersecting);
      },
      {
        root: null,
        threshold: 0.08,
        rootMargin: "0px 0px -40px 0px",
      }
    );

    observer.observe(el);
    return () => observer.disconnect();
  }, [activeConceptId, activeParadigm]);

  // Keep single-pane desktop focus modes synchronized with active tab
  useEffect(() => {
    if (!isMobileViewport && (desktopViewMode === "doc_focus" || desktopViewMode === "report_focus")) {
      setDesktopViewMode(mobileTab === "doc" ? "doc_focus" : "report_focus");
    }
  }, [mobileTab, isMobileViewport, desktopViewMode]);

  useEffect(() => {
    let isMounted = true;
    if (activeConceptId === "client_upload_audit") {
      return;
    }
    setIsLoading(true);

    const isAuditConcept = !["concept_5_hts", "concept_6_valuation"].includes(activeConceptId);
    Promise.all([isAuditConcept ? fetchAudit(activeConceptId) : Promise.resolve(null), fetchAggregateMetrics()])
      .then(([auditRes, metricsRes]) => {
        if (!isMounted) return;
        if (auditRes) setAuditData(auditRes);
        setAggregateMetrics(metricsRes);
      })
      .catch((err) => console.warn("Audit load failed:", err))
      .finally(() => {
        if (isMounted) setIsLoading(false);
      });

    recordTelemetry({
      event_type: "concept_switch",
      concept_id: activeConceptId,
    });

    return () => {
      isMounted = false;
    };
  }, [activeConceptId]);

  const handleCardClick = (id: string) => {
    setActiveDiscrepancyId(id);
    playPseudoHaptic();
    sound.playTick();
    recordTelemetry({
      event_type: "discrepancy_card_selected",
      concept_id: activeConceptId,
      metadata: { discrepancy_id: id },
    });
  };

  const handleBboxClick = (id: string) => {
    setActiveDiscrepancyId(id);
    playPseudoHaptic();
    sound.playLock();
    // On mobile and tablet, seamlessly navigate to the forensic report
    if (typeof window !== "undefined" && window.innerWidth < 1024) {
      setMobileTab("findings");
    } else if (desktopViewMode === "doc_focus") {
      setDesktopViewMode("split");
    }
    const cardEl = document.getElementById(`card-${id}`);
    if (cardEl) {
      cardEl.scrollIntoView({ behavior: "smooth", block: "center" });
    }
  };

  const openReview = () => {
    sound.playLock();
    setIsModalOpen(true);
    setIsMobileNavOpen(false);
  };

  // Headline metrics come straight from the engines (snapshot or live), never from literals
  const displayedExposureAvoided = aggregateMetrics?.penalty_exposure_avoided ?? AGGREGATE_METRICS.penalty_exposure_avoided;
  const displayedCarrierOverbilling = aggregateMetrics?.carrier_overbilling_caught ?? AGGREGATE_METRICS.carrier_overbilling_caught;
  const displayedDrawback = aggregateMetrics?.drawback_unclaimed_unlocked ?? AGGREGATE_METRICS.drawback_unclaimed_unlocked;

  const ladderFinding =
    auditData?.discrepancies.find((d) => d.id === "disc-c1-03") ??
    INITIAL_CUSTOMS_NIGHTMARE_FIXTURE.discrepancies.find((d) => d.id === "disc-c1-03") ??
    null;

  const activeDiscrepancy =
    auditData?.discrepancies.find((d) => d.id === activeDiscrepancyId) ||
    auditData?.discrepancies[0] ||
    null;

  return (
    <div className="min-h-screen w-full max-w-full overflow-x-hidden bg-transparent text-ink-primary flex flex-col font-sans transition-colors duration-200 relative selection:bg-cobalt-600 selection:text-canvas-stone">
      {/* 1. STICKY MINIMALIST DEVELOPER HEADER (56px) */}
      <WorkbenchHeader
        activeParadigm={activeParadigm}
        onParadigmChange={handleParadigmChange}
        isMobileNavOpen={isMobileNavOpen}
        setIsMobileNavOpen={setIsMobileNavOpen}
        onOpenArchitecture={() => {
          sound.playTick();
          setArchitectureModalTab("architecture");
          setIsArchitectureModalOpen(true);
        }}
        onOpenReview={openReview}
      />

      <main id="main-content">
        {/* Mobile Paradigm Switcher Bar (only when menu is closed) */}
        {!isMobileNavOpen && (
          <div className="sm:hidden px-3 py-2 bg-canvas-dark border-b border-terminal-subtle flex items-center justify-center">
            <ParadigmSwitcher activeParadigm={activeParadigm} onChange={handleParadigmChange} showLabel={false} />
          </div>
        )}

        {activeParadigm === "var-2" ? (
          <Var2TriageQueue />
        ) : (
          <>
      {/* 2. ACT 1: ABOVE-THE-FOLD SYSTEMS HERO */}
      <SystemsHeroSection persona={persona} onChangePersona={setPersona} />

      {/* 3. DUAL-PANE AUDIT WORKBENCH (ACT 1 CONTINUED) */}
      <section id="workbench" aria-busy={isLoading} className="max-w-7xl w-full max-w-full overflow-hidden mx-auto px-4 sm:px-6 lg:px-8 py-6">
        {/* Lighthouse heading-order: first in-section heading after the h1 */}
        <h2 className="sr-only">Audit Workbench</h2>
        {/* Scenario Bar: Durban, Long Beach, Steel Drawback */}
        <ScenarioSelectorBar
          activeScenarioId={CORRIDOR_SCENARIOS.find((s) => s.concept_id === activeConceptId)?.id || ""}
          onSelectScenario={(sc: Scenario) => switchConcept(sc.concept_id)}
        />

        {/* Workspace Tab Bar: the six engineering surfaces + Desktop Layout Mode */}
        <WorkspaceTabBar
          pillars={ALL_PILLARS}
          activeConceptId={activeConceptId}
          onSelectConcept={switchConcept}
          onExportAuditPacket={() => exportAuditPacket()}
          desktopViewMode={desktopViewMode}
          setDesktopViewMode={setDesktopViewMode}
        />

        {/* Dynamic Kill Shot Metrics Flash Cards */}
        <KillShotMetricsBar
          exposureAvoided={displayedExposureAvoided}
          carrierOverbilling={displayedCarrierOverbilling}
          drawbackUnlocked={displayedDrawback}
        />

        {/* Hidden Client PDF Input */}
        <input
          ref={fileInputRef}
          type="file"
          accept="application/pdf"
          className="hidden"
          onChange={handleCustomFileUpload}
        />

        <DataSourceBanner uploadError={uploadError} onDismissUploadError={() => setUploadError(null)} />

        {/* Provenance Metadata Bar: document lineage emitted by the engine */}
        <ProvenanceMetadataBar audit={auditData} />

        {/* MAIN WORKBENCH BODY: 6 Pillars or Dual-Pane Canvas */}
        {activeConceptId === "concept_4_sanctions" ? (
          <SanctionsGraphViewer onOpenLeadModal={() => setIsModalOpen(true)} />
        ) : activeConceptId === "concept_5_hts" ? (
          <div className="h-[750px] border border-terminal-subtle rounded-xl overflow-hidden flex flex-col shadow-2xl">
            <HtsClassifierViewer onLeadTrigger={() => setIsModalOpen(true)} />
          </div>
        ) : activeConceptId === "concept_6_valuation" ? (
          <div className="h-[750px] border border-terminal-subtle rounded-xl overflow-hidden flex flex-col shadow-2xl">
            <CustomsValuationViewer onLeadTrigger={() => setIsModalOpen(true)} />
          </div>
        ) : (
          <div
            ref={workbenchContainerRef}
            id="workbench-viewport"
            className="h-[750px] flex flex-col lg:flex-row border border-terminal-subtle rounded-xl overflow-hidden bg-canvas-dark shadow-2xl"
          >
            {/* LEFT PANE: Canvas PDF Viewer */}
            <div
              className={`h-full border-b lg:border-b-0 lg:border-r border-terminal-subtle flex-col overflow-hidden transition-all duration-200 ${
                mobileTab === "doc" ? "flex w-full" : "hidden lg:flex"
              } ${
                desktopViewMode === "doc_focus"
                  ? "lg:w-full lg:flex"
                  : desktopViewMode === "report_focus"
                  ? "lg:hidden"
                  : "lg:w-3/5"
              }`}
            >
              {auditData && (
                <PdfOverlayCanvas
                  documentUrl={auditData.document_url}
                  filename={auditData.document_filename}
                  discrepancies={auditData.discrepancies}
                  activeDiscrepancyId={activeDiscrepancyId}
                  onHoverDiscrepancy={setActiveDiscrepancyId}
                  onClickDiscrepancy={handleBboxClick}
                />
              )}
            </div>

            {/* RIGHT PANE: Interactive Terminal Bay with 3 Sub-Tabs */}
            <AuditTerminalBay
              activeConceptId={activeConceptId}
              auditData={auditData}
              activeDiscrepancy={activeDiscrepancy}
              activeDiscrepancyId={activeDiscrepancyId}
              setActiveDiscrepancyId={setActiveDiscrepancyId}
              handleCardClick={handleCardClick}
              rightTerminalTab={rightTerminalTab}
              setRightTerminalTab={setRightTerminalTab}
              mobileTab={mobileTab}
              setMobileTab={setMobileTab}
              desktopViewMode={desktopViewMode}
            />
          </div>
        )}
      </section>

      {/* 4. ACT 2: INLINE 5-STAGE ARCHITECTURE PIPELINE */}
      <section id="architecture" className="max-w-7xl w-full mx-auto px-4 sm:px-6 lg:px-8 py-8 border-t border-terminal-subtle">
        <InlineArchitectureFlow />
      </section>

      {/* 5. STATUTORY CULPABILITY & PENALTY LADDER (19 U.S.C. § 1592) */}
      <section id="penalty-ladder" className="max-w-7xl w-full mx-auto px-4 sm:px-6 lg:px-8 py-8 border-t border-terminal-subtle">
        <div className="mb-2 max-w-3xl">
          <div className="flex items-center gap-2 font-mono text-xs text-ink-cobalt font-semibold uppercase tracking-wider">
            <Scale className="w-4 h-4" aria-hidden />
            <span>Culpability and prior disclosure</span>
          </div>
          <p className="type-body-dense text-ink-muted mt-1">
            The same loss of duty carries very different statutory maximums depending on culpability. Figures come from the
            engine&apos;s classification finding on {ladderFinding === auditData?.discrepancies.find((d) => d.id === "disc-c1-03") ? "the document on screen" : "the sample customs invoice"}.
          </p>
        </div>
        <PenaltyExposureLadder finding={ladderFinding} />
      </section>

      {/* 6. ACT 4: PRINCIPAL ARCHITECT'S THESIS SIGNED BY SAMUEL */}
      <section id="architect-thesis" className="max-w-7xl w-full mx-auto px-4 sm:px-6 lg:px-8 py-8 border-t border-terminal-subtle">
        <ArchitectThesis onOpenReview={openReview} />
      </section>
          </>
        )}
      </main>

      {/* 9. ENTERPRISE FOOTER */}
      <WorkbenchFooter onOpenReview={openReview} />

      {/* MODALS */}
      <LeadCaptureModal
        isOpen={isModalOpen}
        onClose={() => setIsModalOpen(false)}
        activeConceptId={activeConceptId}
      />

      <ExecutiveDossierModal
        isOpen={isDossierOpen}
        onClose={() => setIsDossierOpen(false)}
        auditData={auditData}
      />

      <FilmTheaterModal
        isOpen={isFilmOpen}
        onClose={() => setIsFilmOpen(false)}
        onOpenLeadModal={() => setIsModalOpen(true)}
      />

      <SystemArchitectureModal
        isOpen={isArchitectureModalOpen}
        onClose={() => setIsArchitectureModalOpen(false)}
        initialTab={architectureModalTab}
      />

      <ExecutiveTourOverlay
        isActive={isTourActive}
        onClose={() => setIsTourActive(false)}
        onOpenArchitectureModal={() => {
          setArchitectureModalTab("architecture");
          setIsArchitectureModalOpen(true);
        }}
      />

      {/* Contextual Floating Navigation Dock */}
      <MobileBottomNavPill
        activeTab={mobileTab}
        discrepancyCount={auditData?.discrepancies.length || 0}
        isVisible={
          isPillInViewport &&
          activeParadigm === "var-1" &&
          !["concept_4_sanctions", "concept_5_hts", "concept_6_valuation"].includes(activeConceptId) &&
          (isMobileViewport || desktopViewMode !== "split")
        }
        onSelectTab={(tab) => {
          sound.playTick();
          setMobileTab(tab);
        }}
      />
    </div>
  );
};

export const DualPaneAuditViewer: React.FC = () => {
  return (
    <FirewallProvider>
      <DualPaneAuditViewerInner />
    </FirewallProvider>
  );
};
