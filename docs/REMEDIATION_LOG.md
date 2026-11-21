# Remediation Log: v2.0.0 Principal Audit (20 Nov 2026)

Each row maps a finding from the external v2 audit to the change that closes it and the test that keeps it closed. Finding IDs live here, not in code comments.

| ID | Finding | Fix | Guarded by |
|---|---|---|---|
| F1 | "SHA-256 provenance" in the UI was a table of textbook test vectors (`e3b0c442…` = SHA-256 of the empty string) | Backend computes `document_sha256` from the audited bytes; the UI renders it (fake table deleted) | `tests/test_provenance_contract.py` |
| F2 | Parser defaults fabricated money ($19,800 drawback from a memo, $350,000 penalty, $204.80 FSC) | Missing fields are `None`; `missing_fields` quarantines; document type needs 4+ independent signals | `tests/test_unseen_documents_and_regressions.py` (memo corpus) |
| F3 | Uploads were layout-verified against, and displayed as, the fixture PDF | `run_audit(parsed_document=…)` uses the upload's own text, boxes and hash; `document_url` is empty and the UI keeps the blob URL | `test_uploaded_findings_are_anchored_to_the_upload_not_the_fixture` |
| F4 | Unparseable real invoices (EUR, generic, rotated) were RELEASED with zero items | Release gate: missing fields or non-USD currency quarantine; locale-aware amounts; Incoterms 2020 enumeration | unseen corpus (8 documents) |
| F5 | 1592 maximums ignored the domestic-value cap and non-revenue tiers; invented floors; wrong prior-disclosure rule; 4x headline | `app/core/penalties.py` implements 1592(c)(1)-(4); default culpability negligence; gross negligence shown as a tier | `test_customs.py`, Hypothesis `test_fuzz_1592_*` |
| F6 | 1505 interest dropped the last day of each quarter and ignored leap years; two interest engines | End-exclusive day count, 366-day denominator in leap years; inline formula removed | `test_1505_interest_counts_every_day` |
| F7 | FY2026 MPF caps invented; no informal-entry fee; no FTA exemption | FY2026 $33.58 / $651.50 (FR Doc. 2025-13869); informal fees; `fta_exempt`; `fiscal_year_for()` | `test_mpf_informal_entry_and_fiscal_year` |
| F8 | 25% duty fallback (including when the rate was `0.00`), invented 1% insurance estimate, stale 301 table | Dated `Ch99Measure` table (8542 at 25% to 2024, 50% from 2025); no fallbacks; parser derives rates from origin and date | `test_zero_lawful_rate_is_not_replaced_by_25_percent`, `test_section_301_semiconductors_are_dated` |
| F9 | Corrupt PDF caused a 500; frontend silently substituted mock data and another entity's sanctions graph | `UnreadablePdfError` mapped to 422/413; frontend `DataSourceBanner`; no substitute records | `test_corrupt_pdfs_are_422_not_500` |
| F10 | Run id did not bind policy or ruleset; decisions lived in React state | `run_digest` per ADR-001; hash-chained SQLite resolutions ledger with REST endpoints; UI rehydrates on load | `test_resolution_ledger_is_hash_chained_and_tamper_evident`, `test_resolution_endpoints_round_trip` |
| F11 | Duplicate ownership edge doubled a stake (30% filed twice → 60%, BLOCK); stale IEEPA maximum | Edge de-duplication on (owner, asset), Decimal percentages; IEEPA $377,700 (2025, unchanged 2026) | `test_fuzz_yente_aggregate_ownership_monotonicity`, probe |
| F12 | CargoWise diff used literal amounts; XSD presented as authoritative; fake "200 OK" eAdaptor simulation | XML built from `AuditResult`; XSD renamed `cargowise_universal_structural_subset.xsd`; simulation removed | `test_cargowise_concept_driven_diff_payload` |
| F13 | Freight engine cited UCC 2-207 and "FMC Docket 21-08"; no 46 CFR Part 541 | 541.7 30-day invoice rule, 541.5/541.6 required information, calendar/business free-time basis, days computed from dates | `test_pdf_field_parser.py`, freight tests |
| F14 | Drawback eligibility asserted (`is_timely = True`, "100%" literal) | 5-year limit from dates, quantity matching, (j)(1)/(j)(2) basis | `test_drawback.py` |
| F15 | Tests restated the implementation | Statute-anchored properties (domestic-value cap, non-revenue tiers, PD rules) and an unseen-document corpus | as above |
| F16 | Claim drift (model names, three throughput figures, ACE Ready, Docling, stale test counts) | One `metrics.ts` (test count + measured benchmark with hardware); `sync_metrics.py` scans all docs and sources; offline data generated from the backend | `sync_metrics.py --check`, `export_frontend_snapshot.py --check` |
| F17 | Audit-ID tags in production comments; 12 lint warnings; hex literals in components | Tags removed (this log replaces them); `next lint --max-warnings 0`; hex colours replaced by tokens and banned by the token linter | CI |
| F18 | Rotation-unaware client boxes; rate limiter keyed on proxy IP; whole upload buffered | pdf.js viewport transform; backend boxes use Tm×CTM, MediaBox origin and /Rotate; trusted-proxy keying; capped chunked read | `test_client_key_*` |

## Not done (out of scope for a code change)

- Validating XML against WiseTech-published schemas requires licensed access to them.
- OCR for scanned documents: scans are held for review instead.
- Section 301 rows marked `verified=False` (8541/8542 List 2 headings, 8501.31, 8504.40, 8507.60 List 4A) should be confirmed against the HTSUS before commercial use.
- 46 CFR 541.6 required-information check covers a subset of fields; confirm the full list against the current eCFR.
