# 🛡️ TradeTech Systems Studio: Deterministic Trade Intelligence & Customs Defense

[![Live Demo](https://img.shields.io/badge/Demo-Live%20Console-0284c7?style=for-the-badge&logo=googlechrome&logoColor=white)](https://sssammyboyyy.github.io/trade-systems-studio/)
[![Whitepaper](https://img.shields.io/badge/Whitepaper-Interactive%20Edition-8b5cf6?style=for-the-badge&logo=googledocs&logoColor=white)](https://sssammyboyyy.github.io/trade-systems-studio/whitepaper/)
[![CI](https://github.com/sssammyboyyy/trade-systems-studio/actions/workflows/ci.yml/badge.svg)](https://github.com/sssammyboyyy/trade-systems-studio/actions/workflows/ci.yml)
[![Tests](https://img.shields.io/badge/Pytest-260%2F260%20Passing-10b981?style=for-the-badge&logo=pytest&logoColor=white)](#-automated-verification)
[![Next.js 15](https://img.shields.io/badge/Next.js-15.5.29-black?style=for-the-badge&logo=nextdotjs&logoColor=white)](https://nextjs.org)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.115+-009688?style=for-the-badge&logo=fastapi&logoColor=white)](https://fastapi.tiangolo.com)
[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg?style=for-the-badge)](LICENSE)

> **Architected by Samuel Rencken**  
> *BCom in Economic Sciences (International Trade) | Principal Systems Architect*  
> **Interactive Live Audit Console:** [https://sssammyboyyy.github.io/trade-systems-studio/](https://sssammyboyyy.github.io/trade-systems-studio/)

---

## 🏛️ Executive Summary & Architectural Moat

Importers, customs brokers and forwarders pay carrier invoices that do not match the contract, leave drawback unclaimed, and carry **19 U.S.C. § 1592** civil penalty exposure from classification, valuation and assist errors on the entry.

Generic language model prompt wrappers fail in regulated international trade because probabilistic text generators hallucinate tariff subheadings, drift during currency and unit conversions, and cannot show the arithmetic behind a figure.

**TradeTech Systems Studio** solves this with an enterprise pre-ingest architecture that pairs **statutory legal reasoning (WCO GRI 1 to 6, 19 U.S.C. § 1401a, 19 U.S.C. § 1592, 19 CFR § 152.103, 31 CFR § 501)** with **strict mathematical determinism (Python `Decimal` serialized end-to-end as strings)** and **local PDF layout extraction (`pypdf` + `LayoutExtractor` on a `[0, 1000)` coordinate grid)**.

> **Scope & Compliance Notice:** TradeTech Systems Studio is engineered as decision-support software for licensed customs brokers, trade compliance teams, and self-filing importers. It does not constitute legal counsel or unlicensed customs brokerage under 19 U.S.C. § 1641; all generated disclosures are watermarked `DRAFT` for licensed broker or customs attorney review.

```
┌────────────────────────────────────────────────────────────────────────────────────────┐
│                                 THE ARCHITECTURAL MOAT                                 │
├─────────────────────────┬──────────────────────────────────────────────────────────────┤
│ Strict Determinism      │ 100% Python Decimal math; string-serialized across API bounds│
│ Local Extraction        │ pypdf text layer; findings anchored to the document's text   │
│ Fail-Closed Invariants  │ Missing fields are None and quarantine; nothing is defaulted │
│ Statutory Accuracy      │ 19 USC 1401a/1592/1313/1505, 46 CFR 541, dated rate tables   │
│ Entity Resolution Graph │ Fail-closed cycle-safe multi-tier OFAC 50% Rule traversal    │
│ WCO GRI State Machine   │ Word-boundary HTS reasoning with mandatory broker review gate│
│ Provenance              │ run id = SHA-256(calc, policy, ruleset, document) + ledger   │
│ Nightmare Suite UI      │ WCAG 2.2 AA dark console with multi-page React-PDF & PII mask│
└─────────────────────────┴──────────────────────────────────────────────────────────────┘
```

---

## 🎯 CargoWise 2026 Positioning Nuance

TradeTech Systems Studio acts as an **Upstream Pre-Ingest and Financial Exception Firewall** deployed ahead of your Transportation Management System (TMS).

1. **Exception Interception:** Intercepts accessorial overbilling and customs valuation discrepancies before shipment data enters downstream TMS workflows.
2. **Standardized Ingest Boundary:** Generates `UniversalShipment`-style XML from the audit result (validated against an in-repo structural subset XSD only; nothing is transmitted to eAdaptor).
3. **Audit-Ready Provenance:** Every finding binds directly to its legal statute and normalized `[0, 1000)` bounding box, giving licensed brokers and operations teams verifiable evidence before releasing carrier disbursements or customs filings.

---

## 🔬 The Six Flagship Enterprise Engines

### 1. Customs Compliance Firewall & 1592 Defense
- **Statutory Authority:** 19 U.S.C. § 1401a, 19 U.S.C. § 1592 & 19 CFR § 152.103.
- **The Threat:** Unitemized CIF freight/insurance risking overstatement, unreported buyer-provided assists, quantity-by-unit-price multiplication mismatches, and HTS code misclassifications (e.g. 8471.30 vs 8542.31).
- **The Defense:** Fail-closed extraction (missing fields quarantine the document) and the statutory maximums of 19 U.S.C. § 1592(c), computed in `app/core/penalties.py`:
  - **Negligence:** lesser of domestic value or 2x the loss of duty (20% of dutiable value if no loss)
  - **Gross negligence:** lesser of domestic value or 4x the loss of duty (40% of dutiable value if no loss)
  - **Fraud:** up to the domestic value
  - **Prior disclosure:** negligence and gross negligence limited to interest on the loss; fraud to 100% of the loss
  - Section 301 rates are dated (e.g. 8542 at 25% to 31 Dec 2024, 50% from 1 Jan 2025) and 1505 interest counts every day (366-day years in leap years).
- **Outcome:** Flags discrepancies before the entry is filed. Culpability is shown as negligence by default; it is a legal determination for counsel.

### 2. Pre-Payment Freight Audit (46 CFR Part 541)
- **Authority:** the service contract or tariff, 46 CFR 545.5, and the OSRA 2022 demurrage and detention billing rule (46 CFR Part 541: invoice within 30 days of the last charge, required invoice information, dispute window).
- **The Threat:** Carriers tacking on unwarranted surcharges: unauthorized chassis splits ($285.00), fuel surcharge billed above the contracted rate (32.5% vs 24.0% on the sample), detention billed inside free time (days counted from the discharge and out-gate dates), and detention invoices that are late or missing required information.
- **The Defense:** Systematic pre-payment invoice interrogation against baseline ocean contract tariffs and weekly published fuel indices, generating carrier dispute packets from computed Decimal values.

### 3. Duty Drawback Harvester (19 U.S.C. § 1313)
- **Statutory Authority:** 19 U.S.C. § 1313 Unused Merchandise & Manufacturing Drawback.
- **The Threat:** Drawback goes unclaimed because import and export records live in different systems.
- **The Defense:** Matches the import entry to the export bill of lading on dates, quantities and basis ((j)(1) direct identification or (j)(2) same 8-digit HTS), enforces the 5-year limit of 1313(r)(1), and refunds 99% of the duty on the matched quantity only.

### 4. Global Sanctions & Corporate Entity Resolution Graph
- **Statutory Authority:** 31 CFR § 501 / OFAC 50 Percent Rule & BIS Entity List / UVL separation.
- **The Threat:** Blocked entities and SDN-listed targets conceal ownership through multi-tiered corporate holding shells where each layer holds under 50%, yet aggregated blocked equity reaches or exceeds 50%.
- **The Defense:** Fail-closed resolution (`UNSCREENED / HOLD` on unknown entities or provider errors) with cycle-safe transitive multi-hop graph traversal against a persistent FollowTheMoney v3 dataset (`yente_ofac_ftm.jsonl`) and RapidFuzz string screening.

### 5. Autonomous Landed Cost & HTS Classification Copilot
- **Statutory Authority:** WCO General Rules of Interpretation (GRI 1 to 6) & 19 CFR § 24.23/24.
- **The Threat:** Single-turn LLM prompts guess 10-digit HTS codes in one shot, bypassing Chapter/Section Notes and generating indefensible entries that fail CBP regulatory audits.
- **The Defense:** Word-boundary hierarchical classification engine evaluating candidate headings and Section notes with element-wise confidence gating. Unmatched goods or low confidence (`confidence < 0.85`) fail closed to `REQUIRES_BROKER_REVIEW / requires_human_review=True` for licensed customs broker adjudication. Aggregates duty, origin-aware Section 301 tariffs, MPF (FY2027 statutory caps $34.58 to $670.86 per 91 FR 48398, with FY2024 to FY2026 historical support), and HMF (0.125%) via Python `Decimal`.

### 6. CBP Assist & Valuation Register (19 CFR § 152.103)
- **Statutory Authority:** 19 U.S.C. § 1401a, 19 CFR § 152.103, and 19 CFR § 162.74 (Prior Disclosure).
- **The Threat:** Importers omit buyer-supplied molds, dies, and foreign engineering design assists, while improperly declaring non-dutiable international ocean freight and insurance in US transaction value.
- **The Defense:** GAAP assist register supporting First Entry and Units Produced amortization methods, deducting non-dutiable international logistics overhead per 19 U.S.C. § 1401a(b)(4)(A), and compiling watermarked `DRAFT` 19 CFR § 162.74 Prior Disclosure worksheets for licensed broker or trade attorney review.

---

## 🏗️ Monorepo Architecture

```
trade-systems-studio/
├── backend-engine/              # High-Precision Python/FastAPI Compliance Engine
│   ├── app/
│   │   ├── api/
│   │   │   ├── deps.py          # Extractor dependency injection
│   │   │   └── endpoints.py     # REST endpoints (/audit, /metrics, /sanctions, /hts, /valuation)
│   │   ├── core/
│   │   │   └── config.py        # Environment settings & static path resolution
│   │   ├── models/
│   │   │   ├── schemas.py          # Strict Pydantic v2 schemas with [0, 1000) bboxes
│   │   │   ├── sanctions_graph.py  # OFAC 50% Rule node/edge graph schemas
│   │   │   ├── hts_models.py       # WCO GRI decision node & landed cost schemas
│   │   │   ├── valuation_models.py # GAAP assist & Prior Disclosure schemas
│   │   │   └── nightmare.py        # Ground-truth scenario representations
│   │   ├── services/
│   │   │   ├── extractor.py        # Core audit engine & physical PDF extraction bridge
│   │   │   ├── layout_extractor.py # Local pypdf layout extractor with [0, 1000) coordinates
│   │   │   ├── sanctions_screener.py # RapidFuzz matcher & fail-closed cycle-safe graph traversal
│   │   │   ├── hts_classifier.py   # Word-boundary WCO GRI 1-6 classifier with broker review gate
│   │   │   ├── valuation_ledger.py # GAAP assist amortization & DRAFT prior disclosure worksheets
│   │   │   ├── cargowise_xml.py    # UniversalShipment-style XML built from the audit result
│   │   │   ├── customs_audit.py    # 19 U.S.C. § 1401a / § 1592 calculation engine
│   │   │   ├── freight_audit.py    # Freight audit engine (contract, free time, 46 CFR Part 541)
│   │   │   ├── drawback_audit.py   # 19 U.S.C. § 1313 drawback engine
│   │   │   ├── ai_classifier.py    # Structured outputs classifier
│   │   │   └── fixture_generator.py# ReportLab 2-page synthetic archival PDF generator
│   │   └── data/
│   │       ├── nightmares/         # Ground-truth 2-page PDF fixtures with synthetic entities
│   │       └── yente_ofac_ftm.jsonl# Persistent FollowTheMoney v3 sanctions dataset (38 records)
│   ├── tests/                   # 260 automated tests (unit, Hypothesis properties, E2E, unseen-document corpus)
│   ├── benchmark.py             # Concurrency benchmarking suite
│   ├── demo.py                  # CLI multi-statute evaluation tool
│   └── main.py
│
├── frontend-dashboard/          # Next.js 15.5.29 App Router "Nightmare Suite" Console
│   ├── src/
│   │   ├── app/
│   │   │   ├── layout.tsx       # Root layout with JetBrains Mono, Inter & Newsreader
│   │   │   ├── page.tsx         # Master page shell
│   │   │   └── globals.css      # WCAG 2.2 AA OKLCH color tokens & high-contrast dark theme
│   │   ├── components/
│   │   │   ├── DualPaneAuditViewer.tsx   # Dual-pane synchronized audit console
│   │   │   ├── PdfOverlayCanvas.tsx     # Multi-page React-PDF renderer with PII redaction toggle
│   │   │   ├── DiscrepancyCard.tsx       # Interactive discrepancy cards with visual diffs
│   │   │   ├── SanctionsGraphViewer.tsx  # Interactive SVG corporate ownership network
│   │   │   ├── HtsClassifierViewer.tsx   # WCO GRI 1-6 decision tree & landed cost calculator
│   │   │   ├── CustomsValuationViewer.tsx # GAAP assist register & DRAFT Prior Disclosure modal
│   │   │   ├── FilmTheaterModal.tsx      # HyperFrames broadcast film theater modal
│   │   │   ├── AmbientMotionBackground.tsx # Living depth layer with ghost statutes
│   │   │   ├── ArchitectThesis.tsx       # Principal architect statement signed by Samuel
│   │   │   ├── ParadigmSwitcher.tsx      # Multi-paradigm console switcher
│   │   │   └── ThreeWayResolutionBar.tsx # Triage resolution bar (Dismiss / Escalate / Settle)
│   │   ├── data/
│   │   │   └── mockData.ts              # Deterministic offline fixture datasets
│   │   └── lib/
│   │       ├── api.ts                   # API client with deterministic offline fallback
│   │       ├── assets.ts                # GitHub Pages asset prefix resolver
│   │       ├── audio.ts                 # Web Audio API dual-frequency micro-haptics
│   │       ├── clientAuditor.ts         # On-device PDF demo heuristic parser
│   │       ├── metrics.ts               # Single source of truth for verified test counts (200)
│   │       └── types.ts                 # Shared TypeScript contracts
│   └── public/
│       ├── film/                        # Keyframe snapshots
│       ├── nightmares/                  # 2-page archival demo PDF fixtures
│       └── pdf.worker.min.mjs           # Local offline PDF.js worker
│
├── docs/                        # Architecture Whitepaper, Benchmarks & ADRs
│   ├── TRADETECH_SYSTEMS_ARCHITECTURE_WHITEPAPER.md # Technical deep dive across all 6 engines
│   ├── PERFORMANCE_AND_SCALE_BENCHMARKS.md      # Latency benchmarks & scaling telemetry
│   └── adr/                                     # Architecture Decision Records (ADR-001 to ADR-004)
│
├── scripts/                     # Automation, CI verification & Playwright test scripts
│   ├── check_em_dashes.py       # Automated zero em-dash / en-dash governance gate
│   ├── sync_metrics.py          # Dynamic pytest-to-UI metric synchronization script
│   ├── run_e2e_playwright.py    # Desktop and mobile end-to-end DOM test
│   └── check_typography_tokens.py # Dual-surface OKLCH typography token gate
│
├── .github/workflows/
│   ├── ci.yml                   # Enterprise CI pipeline: 200-test matrix, ruff, mypy & Next.js build
│   └── deploy-pages.yml         # Automated GitHub Actions Pages deployment
├── docker-compose.yml           # Single-command local stack orchestration
├── GLOSSARY.md                  # International trade & customs statutory glossary
└── LICENSE                      # MIT License
```

---

## ⚡ Automated Verification

```bash
# 1. Verify Backend Engine (Lint, Strict Types, and all 260 unit, property, E2E and unseen-document tests)
cd backend-engine
ruff check app tests
mypy app
pytest -v

# 2. Verify Zero Dash Violations Governance Gate (Mandatory across all files)
cd ..
python scripts/check_em_dashes.py

# 3. Verify Frontend Production Typecheck & Static Export (Next.js 15.5.29)
cd frontend-dashboard
npx tsc --noEmit
npm run build

# 4. Run Executive CLI Multi-Statute Suite Evaluation (<1s)
cd ../backend-engine
python demo.py
```

---

## 🚀 Running Locally

### Backend Setup
```bash
cd backend-engine
python -m venv .venv
# On Windows: .venv\Scripts\activate | On macOS/Linux: source .venv/bin/activate
pip install -r requirements.txt
uvicorn main:app --reload --port 8000
```

### Frontend Setup
```bash
cd frontend-dashboard
npm install
npm run dev
# Open http://localhost:3000
```

*Note: The frontend operates in deterministic zero-key fallback mode by default, allowing full review of all scenarios without an active backend or cloud API keys.*

---

## 👤 The Principal Architect

**Samuel Rencken**  
*BCom in Economic Sciences (International Trade) | North-West University (NWU)*  
*Principal Systems Architect & Forward-Deployed TradeTech Lead*  

Samuel operates at the rare intersection of statutory trade legal mechanics (19 U.S.C. § 1592, 19 CFR § 152.103, WCO GRI 1 to 6) and deterministic, zero-drift systems engineering. TradeTech Systems Studio demonstrates how to replace fragile language model wrappers with mathematically verifiable, high-throughput pre-audit firewalls built for global supply chain scale.

- **Interactive Live Console:** [https://sssammyboyyy.github.io/trade-systems-studio/](https://sssammyboyyy.github.io/trade-systems-studio/)
- **Technical Whitepaper:** [https://sssammyboyyy.github.io/trade-systems-studio/whitepaper/](https://sssammyboyyy.github.io/trade-systems-studio/whitepaper/)
- **GitHub Monorepo:** [https://github.com/sssammyboyyy/trade-systems-studio](https://github.com/sssammyboyyy/trade-systems-studio)
