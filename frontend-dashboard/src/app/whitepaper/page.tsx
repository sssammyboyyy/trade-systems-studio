"use client";

import React, { useState } from "react";
import Link from "next/link";
import {
  ArrowLeft,
  Printer,
  ExternalLink,
  ShieldCheck,
  CheckCircle2,
  Cpu,
  Terminal,
  FileText,
  ChevronRight,
  BookOpen,
  Scale,
  Activity,
  Layers,
  Lock
} from "lucide-react";
import { sound } from "@/lib/audio";
import { VERIFIED_PYTEST_COUNT } from "@/lib/metrics";

export default function WhitepaperPage() {
  const [activeSection, setActiveSection] = useState("abstract");

  const scrollTo = (id: string) => {
    sound.playTick();
    setActiveSection(id);
    const element = document.getElementById(id);
    if (element) {
      element.scrollIntoView({ behavior: "smooth" });
    }
  };

  const handlePrint = () => {
    sound.playTick();
    if (typeof window !== "undefined") {
      window.print();
    }
  };

  const testBadgeLabel = `${VERIFIED_PYTEST_COUNT}/${VERIFIED_PYTEST_COUNT} Tests Verified`;

  return (
    <div className="min-h-screen bg-transparent text-canvas-stone selection:bg-cyan-500 selection:text-black">
      {/* Top Sticky Header */}
      <header className="sticky top-0 z-40 bg-terminal-slate/90 backdrop-blur-md border-b border-terminal-subtle px-4 sm:px-8 py-3.5 flex items-center justify-between">
        <div className="flex items-center gap-3">
          <Link
            href="/"
            onClick={() => sound.playTick()}
            className="flex items-center gap-1.5 px-3 py-1.5 rounded bg-terminal-slate border border-terminal-subtle hover:border-slate-500 text-xs font-mono text-slate-300 hover:text-ink-primary transition-all group"
          >
            <ArrowLeft className="w-3.5 h-3.5 text-slate-400 group-hover:-translate-x-0.5 transition-transform" />
            <span>Live Console</span>
          </Link>
          <div className="h-4 w-px bg-slate-700 hidden sm:block" />
          <div className="hidden sm:flex items-center gap-2 text-xs font-mono">
            <span className="text-ink-primary font-bold">TradeTech Systems Studio</span>
            <span className="text-slate-400">•</span>
            <span className="text-cyan-400">Technical Whitepaper</span>
          </div>
        </div>

        <div className="flex items-center gap-2.5">
          <button
            type="button"
            onClick={handlePrint}
            aria-label="Print or save technical whitepaper as PDF"
            className="flex items-center gap-1.5 px-3 py-1.5 rounded bg-terminal-slate border border-terminal-subtle hover:border-slate-500 text-xs font-mono text-slate-300 hover:text-ink-primary transition-all"
          >
            <Printer className="w-3.5 h-3.5 text-slate-400" />
            <span className="hidden sm:inline">Print / PDF</span>
          </button>
          <a
            href="https://github.com/sssammyboyyy/trade-systems-studio"
            target="_blank"
            rel="noreferrer"
            className="flex items-center gap-1.5 px-3 py-1.5 rounded bg-cyan-500 hover:bg-cyan-400 text-black text-xs font-mono font-bold uppercase tracking-wider transition-all"
          >
            <span>GitHub Monorepo</span>
            <ExternalLink className="w-3.5 h-3.5" />
          </a>
        </div>
      </header>

      {/* Main Container */}
      <div className="max-w-7xl mx-auto px-4 sm:px-8 py-8 sm:py-12 grid grid-cols-1 lg:grid-cols-12 gap-8">
        {/* Left Sticky Sidebar / Table of Contents */}
        <aside className="lg:col-span-3" aria-label="Whitepaper Table of Contents">
          <div className="sticky top-20 rounded-xl bg-terminal-slate border border-terminal-subtle p-4 space-y-4">
            <div className="text-xs font-bold uppercase tracking-wider text-slate-400 font-mono flex items-center gap-2">
              <BookOpen className="w-3.5 h-3.5 text-cyan-400" />
              <span>Table of Contents</span>
            </div>

            <nav className="space-y-1 font-mono text-xs" aria-label="Section navigation">
              {[
                { id: "abstract", label: "1. Abstract", icon: FileText },
                { id: "determinism", label: "2. Arithmetic & Fail-Closed Core", icon: Scale },
                { id: "state-machine", label: "3. WCO GRI 1 to 6 Classification", icon: Layers },
                { id: "sanctions-graph", label: "4. OFAC 50% Rule Graph", icon: Activity },
                { id: "valuation-ledger", label: "5. Assist Valuation & Disclosures", icon: ShieldCheck },
                { id: "benchmarks", label: "6. Verification & Hardening", icon: Cpu },
                { id: "conclusion", label: "7. Scope & Governance", icon: Terminal },
              ].map((item) => {
                const Icon = item.icon;
                const isActive = activeSection === item.id;
                return (
                  <button
                    type="button"
                    key={item.id}
                    onClick={() => scrollTo(item.id)}
                    aria-current={isActive ? "location" : undefined}
                    className={`w-full text-left px-2.5 py-1.5 rounded transition-all flex items-center justify-between group ${
                      isActive
                        ? "bg-cyan-950/40 text-cyan-400 border border-cyan-500/30 font-semibold"
                        : "text-slate-400 hover:text-slate-200 hover:bg-slate-800/40"
                    }`}
                  >
                    <div className="flex items-center gap-2 truncate">
                      <Icon className={`w-3.5 h-3.5 shrink-0 ${isActive ? "text-cyan-400" : "text-slate-400"}`} />
                      <span className="truncate">{item.label}</span>
                    </div>
                    <ChevronRight className={`w-3 h-3 transition-transform ${isActive ? "text-cyan-400 translate-x-0.5" : "text-transparent"}`} />
                  </button>
                );
              })}
            </nav>

            <div className="pt-3 border-t border-terminal-subtle text-[11px] font-mono text-slate-400 space-y-1">
              <div>Author: <span className="text-slate-300 font-semibold">Samuel Rencken</span></div>
              <div>Degree: <span className="text-slate-300">BCom Economic Sciences (Intl. Trade)</span></div>
              <div>Status: <span className="text-emerald-400 font-semibold">{testBadgeLabel}</span></div>
            </div>
          </div>
        </aside>

        {/* Right Article Body */}
        <main id="main-content" className="lg:col-span-9 space-y-12">
          {/* Paper Title Block */}
          <div className="p-6 sm:p-8 rounded-2xl bg-terminal-slate border border-terminal-subtle space-y-4">
            <div className="flex flex-wrap items-center gap-2">
              <span className="px-2.5 py-1 text-xs font-mono font-semibold bg-cyan-500/10 text-cyan-400 border border-cyan-500/30 rounded">
                Systems Architecture Whitepaper (v2.0)
              </span>
              <span className="px-2.5 py-1 text-xs font-mono font-semibold bg-emerald-500/10 text-emerald-400 border border-emerald-500/30 rounded flex items-center gap-1">
                <CheckCircle2 className="w-3.5 h-3.5" />
                <span>{testBadgeLabel}</span>
              </span>
              <span className="px-2.5 py-1 text-xs font-mono font-semibold bg-slate-800/80 text-slate-300 border border-slate-700 rounded flex items-center gap-1">
                <Lock className="w-3.5 h-3.5 text-cyan-400" />
                <span>Fail-Closed Architecture</span>
              </span>
            </div>

            <h1 className="text-2xl sm:text-4xl font-bold tracking-tight text-ink-primary font-sans leading-tight">
              Deterministic Trade Compliance Engineering: Python Decimal Invariants, Fail-Closed Classification Gating, and Cycle-Safe Corporate Sanctions Graphs
            </h1>

            <div className="flex flex-wrap items-center gap-4 text-xs font-mono text-slate-400 pt-2 border-t border-terminal-subtle">
              <div>Author: <span className="text-ink-primary font-bold">Samuel Rencken</span></div>
              <div>•</div>
              <div>Academic Foundation: <span className="text-cyan-400">BCom in Economic Sciences (International Trade), North-West University (NWU)</span></div>
              <div>•</div>
              <div>Stack: <span className="text-emerald-400">FastAPI + Next.js 15.5.29</span></div>
            </div>
          </div>

          {/* SECTION 1: ABSTRACT */}
          <section id="abstract" className="space-y-4">
            <h2 className="text-xl font-bold text-ink-primary font-mono flex items-center gap-2 border-b border-terminal-subtle pb-2">
              <span className="text-cyan-400">1.</span>
              <span>Abstract</span>
            </h2>
            <p className="text-slate-300 text-sm leading-relaxed">
              Commercial trade operations and customs compliance represent an asymmetric operational surface: mid-market enterprise importers lose <strong className="text-amber-400">5% to 15% of total freight spend</strong> to carrier accessorial overbilling and face severe civil monetary penalties under <strong className="text-red-400">19 U.S.C. § 1592 ($100k to $2.4M+)</strong> due to line-item arithmetic discrepancies, assist omissions under 19 CFR § 152.103, and Harmonized Tariff Schedule (HTS) misclassifications.
            </p>
            <p className="text-slate-300 text-sm leading-relaxed">
              Naive generative AI wrappers fail in regulated trade workflows because probabilistic text models hallucinate statutory citations, introduce binary floating-point rounding drift, and fail open on missing data or unrecognized commodities. TradeTech Systems Studio addresses these failure modes with a deterministic decision-support architecture built for licensed customs brokers, compliance engineers, and self-filing importers.
            </p>

            <div className="p-4 rounded-xl bg-terminal-slate border border-terminal-subtle space-y-2">
              <div className="text-xs font-bold uppercase tracking-wider text-cyan-400 font-mono">
                Four Non-Negotiable Architectural Invariants:
              </div>
              <ul className="space-y-1.5 text-xs font-mono text-slate-300">
                <li className="flex items-start gap-2">
                  <span className="text-cyan-400 font-bold">•</span>
                  <span><strong>End-to-End Decimal Determinism:</strong> Absolute ban on LLM arithmetic; 100% Python <code className="text-emerald-300">decimal.Decimal</code> (<code className="text-emerald-300">ROUND_HALF_UP</code>) serialized as exact strings across REST API boundaries.</span>
                </li>
                <li className="flex items-start gap-2">
                  <span className="text-cyan-400 font-bold">•</span>
                  <span><strong>Physical Layout Grounding & Fail-Closed Validation:</strong> Local <code className="text-cyan-300">pypdf</code> layout extraction normalized to a strict <code className="text-cyan-300">[0, 1000)</code> grid; empty or missing input payloads return $0 findings rather than fabricated figures.</span>
                </li>
                <li className="flex items-start gap-2">
                  <span className="text-cyan-400 font-bold">•</span>
                  <span><strong>Fail-Closed WCO GRI Classification Gating:</strong> Word-boundary heading evaluation where unmatched commodities or low confidence (<code className="text-amber-300">Conf(e) &lt; 0.85</code>) route automatically to licensed broker review.</span>
                </li>
                <li className="flex items-start gap-2">
                  <span className="text-cyan-400 font-bold">•</span>
                  <span><strong>Cycle-Safe OFAC 50% Rule Traversal:</strong> Transitive multi-hop ownership aggregation against a persistent FollowTheMoney v3 dataset (<code className="text-cyan-300">yente_ofac_ftm.jsonl</code>) with fail-closed <code className="text-red-300">HOLD</code> on unknown entities and strict BIS vs. OFAC regime separation.</span>
                </li>
              </ul>
            </div>
          </section>

          {/* SECTION 2: ARITHMETIC DETERMINISM */}
          <section id="determinism" className="space-y-4">
            <h2 className="text-xl font-bold text-ink-primary font-mono flex items-center gap-2 border-b border-terminal-subtle pb-2">
              <span className="text-cyan-400">2.</span>
              <span>Arithmetic Determinism & Fail-Closed Input Contracts</span>
            </h2>

            <div className="space-y-3 text-sm text-slate-300 leading-relaxed">
              <h3 className="text-base font-bold text-ink-primary font-mono">2.1 Eliminating Floating-Point Drift Across the Wire</h3>
              <p>
                In IEEE 754 double-precision floating-point arithmetic, binary approximations introduce silent representation drift:
              </p>

              <div className="p-3 rounded-lg bg-canvas-dark border border-red-500/30 text-xs font-mono text-red-300 overflow-x-auto">
                0.1 + 0.2 = 0.3000000000000000444089209850062616169452667236328125 ≠ 0.3
              </div>

              <p>
                Under <strong>19 CFR § 152.103</strong> and <strong>19 U.S.C. § 1401a</strong>, declared customs transaction value must reflect the exact price paid or payable (excluding separately identified non-dutiable international freight and marine insurance on US entries). Discrepancies between line-item extensions and summary declarations risk CBP Form 28 inquiries and 19 U.S.C. § 1592 civil penalties:
              </p>

              <div className="grid grid-cols-1 sm:grid-cols-2 gap-3 text-xs font-mono">
                <div className="p-3 rounded bg-terminal-slate border border-terminal-subtle">
                  <div className="text-slate-400">Negligence Penalty Exposure (19 U.S.C. § 1592)</div>
                  <div className="text-sm font-bold text-amber-400 mt-1">Up to 2x loss of duty (lesser of domestic value)</div>
                </div>
                <div className="p-3 rounded bg-terminal-slate border border-terminal-subtle">
                  <div className="text-slate-400">Gross Negligence Penalty Exposure</div>
                  <div className="text-sm font-bold text-red-400 mt-1">Up to 4x loss of duty (lesser of domestic value)</div>
                </div>
              </div>

              <h3 className="text-base font-bold text-ink-primary font-mono pt-3">2.2 String-Serialized Python Decimal & Zero-Fabrication Guard</h3>
              <p>
                Every financial calculation in TradeTech Systems Studio runs exclusively in Python <code className="text-emerald-300">decimal.Decimal</code>, serializes monetary fields as exact decimal strings in JSON responses (preventing JavaScript IEEE-754 parse drift at the API boundary), and validates required fields before computing findings so empty inputs always return $0.00 exposure:
              </p>

              <div className="p-4 rounded-lg bg-canvas-dark border border-terminal-subtle font-mono text-xs text-slate-300 overflow-x-auto">
                <pre className="text-emerald-400 leading-relaxed">
{`from decimal import Decimal, ROUND_HALF_UP

def quantize_currency(value: Decimal) -> Decimal:
    """Enforces exact statutory half-up currency quantization."""
    return value.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)`}
                </pre>
              </div>

              <p>
                Merchandise Processing Fees (MPF capped between FY2027 statutory minimum $34.58 and maximum $670.86 per 91 FR 48398 / 19 CFR § 24.23, with FY2024 to FY2026 historical support), origin-aware Section 301 Chapter 99 tariffs, Harbor Maintenance Fees (0.125% under 19 CFR § 24.24), FMC Docket 21-08 freight audit checks (explicitly distinguishing <code className="text-cyan-300">0</code> free days from <code className="text-cyan-300">None</code>), and 99% Section 1313 Duty Drawback claims (with 5-year time-bar enforcement) are fuzz-tested with Hypothesis across {VERIFIED_PYTEST_COUNT} automated tests.
              </p>
            </div>
          </section>

          {/* SECTION 3: WCO GRI 1-6 STATE MACHINE */}
          <section id="state-machine" className="space-y-4">
            <h2 className="text-xl font-bold text-ink-primary font-mono flex items-center gap-2 border-b border-terminal-subtle pb-2">
              <span className="text-cyan-400">3.</span>
              <span>Hierarchical WCO GRI 1 to 6 Classification & Broker Review Gate</span>
            </h2>

            <div className="space-y-3 text-sm text-slate-300 leading-relaxed">
              <p>
                Flat prompt-based classification violates international customs law because tariff determination under the World Customs Organization (WCO) General Rules of Interpretation is strictly hierarchical and path-dependent. Worse, fallback switches that default unrecognized commodities to a preset tariff code create direct 19 U.S.C. § 1592 misclassification liability.
              </p>

              <div className="p-4 rounded-lg bg-terminal-slate border border-terminal-subtle font-mono text-xs space-y-2">
                <div className="text-cyan-400 font-bold">Hierarchical Code Formulation:</div>
                <div className="text-ink-primary text-sm">
                  y = concat(c, h, s₁, s₂, t)
                </div>
                <div className="text-slate-400 text-[11px] leading-relaxed">
                  where c is the 2-digit Chapter, h is the 4-digit Heading, s₁ is the 6-digit Subheading, s₂ is the 8-digit U.S. Tariff Rate line, and t is the 10-digit Statistical Reporting Suffix.
                </div>
              </div>

              <h3 className="text-base font-bold text-ink-primary font-mono pt-3">3.2 Word-Boundary Matching & Fail-Closed Escalation</h3>
              <p>
                The classifier enforces strict regex word boundaries (preventing substring collisions such as matching &quot;esc&quot; inside &quot;description&quot; or &quot;telescope&quot;). Any unrecognized product or multi-component article scoring below <code className="text-amber-400">Conf(e) &lt; 0.85</code> fails closed:
              </p>

              <div className="grid grid-cols-1 sm:grid-cols-3 gap-3 text-xs font-mono">
                <div className="p-3 rounded bg-terminal-slate border border-terminal-subtle">
                  <div className="text-amber-400 font-bold">1. Unclassified Fallback</div>
                  <div className="text-slate-400 mt-1">Unmatched commodities return confidence 0.0 and explicit unclassified status rather than guessing.</div>
                </div>
                <div className="p-3 rounded bg-terminal-slate border border-terminal-subtle">
                  <div className="text-red-400 font-bold">2. Auto-Filing Halt</div>
                  <div className="text-slate-400 mt-1">Holds the document for review whenever a finding is critical or below 0.85 confidence, or a required field is missing.</div>
                </div>
                <div className="p-3 rounded bg-terminal-slate border border-terminal-subtle">
                  <div className="text-cyan-400 font-bold">3. Broker Adjudication</div>
                  <div className="text-slate-400 mt-1">Surfaces conflicting Section/Chapter notes with visual cues for licensed customs broker sign-off.</div>
                </div>
              </div>
            </div>
          </section>

          {/* SECTION 4: OFAC 50% GRAPH */}
          <section id="sanctions-graph" className="space-y-4">
            <h2 className="text-xl font-bold text-ink-primary font-mono flex items-center gap-2 border-b border-terminal-subtle pb-2">
              <span className="text-cyan-400">4.</span>
              <span>Fail-Closed Multi-Hop Corporate Sanctions Graph (OFAC 50% Rule)</span>
            </h2>

            <div className="space-y-3 text-sm text-slate-300 leading-relaxed">
              <h3 className="text-base font-bold text-ink-primary font-mono">4.1 Statutory Mandate (31 CFR § 501) & Regime Separation</h3>
              <p>
                Under U.S. Treasury Office of Foreign Assets Control (OFAC) guidance, any entity owned <strong>50 percent or more in the aggregate</strong>, directly or indirectly, by one or more blocked persons is itself blocked by operation of law. Crucially, the engine models <strong>OFAC SDN blocking</strong> separately from <strong>BIS Entity List / Unverified List (UVL) export controls</strong> so distinct legal regimes are never conflated.
              </p>

              <div className="p-4 rounded-lg bg-canvas-dark border border-cyan-500/30 font-mono text-xs text-slate-300 overflow-x-auto">
                <pre className="text-cyan-300 leading-tight">
{`┌────────────────────────────────────────────────────────────────────────┐
│            OFAC 50% RULE TRANSITIVE & CYCLE-SAFE RESOLUTION            │
├────────────────────────────────────────────────────────────────────────┤
│  [SDN Blocked] Holding Shell A (100%) ──> Mid-Tier Sub (60% -> 60%)    │
│                                                                        │
│  [SDN Blocked] Group B (30%) + Group C (25%) ──> Target (55% AGG)      │
│                                                  STATUS: BLOCKED       │
│  [Unknown Entity / Outage] ───────────────────> STATUS: UNSCREENED/HOLD│
│  [Circular Shell Cycle]    ───────────────────> Visited-Set Guarded    │
└────────────────────────────────────────────────────────────────────────┘`}
                </pre>
              </div>

              <p>
                Backed by a persistent 37-record FollowTheMoney v3 dataset (<code className="text-cyan-300">yente_ofac_ftm.jsonl</code>), the screener executes cycle-safe OFAC FAQ 401 cascade ownership aggregation across multi-hop chains, fails closed (<code className="text-red-300">UNSCREENED_HOLD</code>) on unknown entities or upstream Yente outages, and combines normalized RapidFuzz token-sort, token-set, and partial-ratio scoring to catch transliteration variants.
              </p>
            </div>
          </section>

          {/* SECTION 5: CBP ASSISTS & PRIOR DISCLOSURE */}
          <section id="valuation-ledger" className="space-y-4">
            <h2 className="text-xl font-bold text-ink-primary font-mono flex items-center gap-2 border-b border-terminal-subtle pb-2">
              <span className="text-cyan-400">5.</span>
              <span>CBP Assist Valuation Ledger & DRAFT Prior Disclosure Worksheets</span>
            </h2>

            <div className="space-y-3 text-sm text-slate-300 leading-relaxed">
              <h3 className="text-base font-bold text-ink-primary font-mono">5.1 Statutory Valuation & Assist Apportionment (19 U.S.C. § 1401a / 19 CFR § 152.103)</h3>
              <p>
                Under 19 U.S.C. § 1401a(h)(1)(A), buyer-provided assists (tools, dies, molds, components, and foreign engineering design supplied free of charge or at reduced cost) must be apportioned and added to transaction value. Simultaneously, under 19 U.S.C. § 1401a(b)(4)(A), separately identified international freight and marine insurance are excluded from US dutiable transaction value.
              </p>

              <div className="grid grid-cols-1 sm:grid-cols-2 gap-3 text-xs font-mono">
                <div className="p-3 rounded bg-terminal-slate border border-terminal-subtle">
                  <div className="text-slate-400">Unit Apportionment Formula</div>
                  <div className="text-sm font-bold text-cyan-400 mt-1">Assist Cost / Anticipated Units</div>
                </div>
                <div className="p-3 rounded bg-terminal-slate border border-terminal-subtle">
                  <div className="text-slate-400">US Transaction Value Deductions</div>
                  <div className="text-sm font-bold text-emerald-400 mt-1">Exclude Intl. Freight &amp; Insurance</div>
                </div>
              </div>

              <h3 className="text-base font-bold text-ink-primary font-mono pt-3">5.2 Watermarked DRAFT Prior Disclosure Worksheets (19 CFR § 162.74)</h3>
              <p>
                When unapportioned assists or valuation discrepancies are detected on US port entries, the register compiles an itemized <strong>DRAFT Prior Disclosure worksheet</strong> under 19 U.S.C. § 1592(c)(4) for review, verification, and filing by a licensed customs broker or trade attorney. Where all statutory conditions are met (timely submission prior to formal CBP investigation, accurate tender of lawful duty loss plus 19 U.S.C. § 1505 statutory interest, and verified scope), prior disclosure can mitigate negligence or gross negligence penalty exposure down to statutory interest.
              </p>

              <div className="p-4 rounded-xl bg-amber-950/20 border border-amber-500/30 text-xs font-mono text-amber-200">
                <strong>Legal Boundary Safeguard:</strong> Generated worksheets are explicitly watermarked <code className="text-amber-300">DRAFT FOR LICENSED BROKER / ATTORNEY REVIEW</code> and never sign as &quot;Counsel of Record&quot; or represent legal advice.
              </div>
            </div>
          </section>

          {/* SECTION 6: VERIFICATION & HARDENING */}
          <section id="benchmarks" className="space-y-4">
            <h2 className="text-xl font-bold text-ink-primary font-mono flex items-center gap-2 border-b border-terminal-subtle pb-2">
              <span className="text-cyan-400">6.</span>
              <span>Automated Verification, Security Hardening & CI Gates</span>
            </h2>

            <div className="p-4 rounded-xl bg-terminal-slate border border-terminal-subtle space-y-3">
              <div className="flex flex-wrap items-center justify-between gap-2">
                <div className="text-xs font-bold uppercase tracking-wider text-ink-primary font-mono">
                  Enforced CI Quality & Security Matrix
                </div>
                <span className="px-2 py-0.5 text-[10px] font-mono bg-emerald-500/20 text-emerald-400 border border-emerald-500/40 rounded font-bold">
                  {testBadgeLabel}
                </span>
              </div>

              <div className="overflow-x-auto">
                <table className="w-full text-left type-mono-data tabular-nums">
                  <thead>
                    <tr className="border-b border-terminal-subtle text-ink-muted">
                      <th className="py-2 pr-4">Verification Layer</th>
                      <th className="py-2 pr-4">Scope & Enforcement</th>
                      <th className="py-2">Status</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-terminal-subtle text-ink-secondary">
                    <tr>
                      <td className="py-2 pr-4 text-ink-primary font-bold">Pytest Suite (Py 3.11 &amp; 3.12)</td>
                      <td className="py-2 pr-4 text-cyan-300">{VERIFIED_PYTEST_COUNT} backend tests (unit, Hypothesis property tests, end-to-end API, and an unseen-document corpus)</td>
                      <td className="py-2 text-emerald-400 font-bold">PASS</td>
                    </tr>
                    <tr>
                      <td className="py-2 pr-4 text-ink-primary font-bold">Static Analysis & Types</td>
                      <td className="py-2 pr-4 text-cyan-300">Ruff lint (0 errors), Mypy strict (23 files), TypeScript strict (`tsc --noEmit`)</td>
                      <td className="py-2 text-emerald-400 font-bold">PASS</td>
                    </tr>
                    <tr>
                      <td className="py-2 pr-4 text-ink-primary font-bold">API & Security Controls</td>
                      <td className="py-2 pr-4 text-cyan-300">Strict CORS allowlist, Pydantic EmailStr + max_length + rate limiting, Next.js 15.5.29</td>
                      <td className="py-2 text-emerald-400 font-bold">VERIFIED</td>
                    </tr>
                    <tr>
                      <td className="py-2 pr-4 text-ink-primary font-bold">Document & XML Provenance</td>
                      <td className="py-2 pr-4 text-cyan-300">Byte-deterministic 2-page PDF fixtures, SHA-256 content-addressed CargoWise XML</td>
                      <td className="py-2 text-emerald-400 font-bold">VERIFIED</td>
                    </tr>
                    <tr>
                      <td className="py-2 pr-4 text-ink-primary font-bold">Frontend Accessibility</td>
                      <td className="py-2 pr-4 text-cyan-300">WCAG 2.2 AA contrast (6.96:1 to 7.47:1), ARIA landmarks, PII redaction toggle</td>
                      <td className="py-2 text-emerald-400 font-bold">VERIFIED</td>
                    </tr>
                    <tr>
                      <td className="py-2 pr-4 text-ink-primary font-bold">Floating-Point Drift</td>
                      <td className="py-2 pr-4 text-emerald-400 font-bold">0.0000000000000000 (Decimal string API contract)</td>
                      <td className="py-2 text-emerald-400 font-bold">PASS</td>
                    </tr>
                  </tbody>
                </table>
              </div>
              <p className="text-[11px] font-mono text-slate-400 pt-1">
                Note: In-memory engine microbenchmarks (`benchmark.py`) measure structured payload throughput separately from full PDF I/O parsing and write results to isolated artifact paths without mutating tracked repository files.
              </p>
            </div>
          </section>

          {/* SECTION 7: CONCLUSION & SCOPE */}
          <section id="conclusion" className="space-y-4">
            <h2 className="text-xl font-bold text-ink-primary font-mono flex items-center gap-2 border-b border-terminal-subtle pb-2">
              <span className="text-cyan-400">7.</span>
              <span>Scope, Governance & Architectural Summary</span>
            </h2>

            <div className="p-6 rounded-2xl bg-terminal-slate border border-cobalt-500/30 space-y-4">
              <p className="text-sm text-slate-300 leading-relaxed">
                By grounding trade intelligence in <strong>end-to-end Python Decimal determinism</strong>, <strong>local PDF layout grounding</strong>, <strong>fail-closed classification and sanctions invariants</strong>, and <strong>transparent legal boundaries</strong>, TradeTech Systems Studio demonstrates production-disciplined systems engineering for global customs and freight compliance.
              </p>

              <div className="p-3 rounded-lg bg-canvas-dark border border-terminal-subtle text-xs font-mono text-slate-400 leading-relaxed">
                <strong className="text-slate-200">Intended Use Notice:</strong> TradeTech Systems Studio is an open-source technical portfolio and compliance decision-support platform designed for licensed customs brokers and self-filing importers. It does not perform unlicensed customs business under 19 U.S.C. § 1641 or provide legal advice. Client-side PDF uploads execute as a transparent browser demo heuristic and never issue compliance certifications.
              </div>

              <div className="flex flex-wrap items-center gap-3 pt-2">
                <Link
                  href="/"
                  onClick={() => sound.playTick()}
                  className="px-4 py-2.5 rounded bg-cobalt-500 hover:bg-cobalt-400 text-black font-mono font-bold text-xs uppercase tracking-wider transition-all shadow-lg shadow-cobalt-950/50"
                >
                  Explore Interactive Console
                </Link>

                <a
                  href="https://github.com/sssammyboyyy/trade-systems-studio"
                  target="_blank"
                  rel="noreferrer"
                  className="px-4 py-2.5 rounded bg-terminal-slate hover:bg-slate-800 text-slate-200 border border-terminal-subtle font-mono text-xs transition-colors flex items-center gap-1.5"
                >
                  <span>{`Review Codebase (${VERIFIED_PYTEST_COUNT}/${VERIFIED_PYTEST_COUNT} Tests)`}</span>
                  <ExternalLink className="w-3.5 h-3.5" />
                </a>
              </div>
            </div>
          </section>
        </main>
      </div>
    </div>
  );
}
