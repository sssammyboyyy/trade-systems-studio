# ADR-001: Deterministic Statutory Kernel vs. Probabilistic LLMs

- **Status:** Accepted (amended 2026-11-20: provenance and fail-closed extraction)
- **Deciders:** Samuel (Principal Architect), TradeTech Governance
- **Date:** 2026-11-16
- **Technical Invariant:** 100% `decimal.Decimal` (`ROUND_HALF_UP`), zero LLM arithmetic, no guessed inputs.

---

## Context
Trade compliance audits carry civil penalty liabilities under 19 U.S.C. 1592 (statutory maximums of 2x or 4x the loss of duty for negligence and gross negligence, each capped by domestic value; up to domestic value for fraud), detention and demurrage billing rules under 46 CFR Part 541, and valuation rules under 19 U.S.C. 1401a.

Large Language Models are probabilistic token generators prone to numerical hallucination and IEEE-754 drift (for example `$132000.0000000002`). Passing financial calculations to an LLM exposes importers of record to statutory liability and would invalidate a prior disclosure.

## Decision
1. **Statutory kernel:** all duty, fee (MPF/HMF), penalty, interest, drawback and overbilling arithmetic runs in a stateless Python kernel using `decimal.Decimal` with `ROUND_HALF_UP`. Rate tables are dated (MPF by fiscal year, Section 301 by effective date, IEEPA maximum by year) and looked up for the date they apply to.
2. **No guessed inputs:** a field that is not in the document is `None`. Engines produce no dollar amount from a missing input, and the extractor quarantines any document with missing required fields (`missing_fields`, `quarantine_reasons`).
3. **Statutory floor invariant:** tenant tolerances in `engagement_policy` apply only to commercial freight tolerance; `statutory_floor_enforced: True` means no federal liability is waived by configuration.
4. **Role of LLMs:** the optional Gemini classifier (`GEMINI_CLASSIFIER_MODEL`, default `gemini-2.5-flash`) may add GRI reasoning text to a classification finding. It never produces an amount and is off when no API key is configured.
5. **Content-addressed provenance:** every audit emits
   `run_digest = SHA-256(calc_version | canonical(engagement_policy) | ruleset_hash | document_sha256)`,
   where `ruleset_hash` is the SHA-256 of the rule-module sources (`app/services/extractor.py: _RULE_MODULES`) and `document_sha256` is the hash of the audited bytes. `audit_run_id` is its 20-character prefix. Wall-clock time is recorded separately in `executed_at`, and the date used for interest and time limits in `as_of_date`, so replays are reproducible.
6. **Decisions are recorded, not held in UI state:** analyst approvals, escalations and HTS overrides are appended to a hash-chained ledger keyed by `audit_run_id` (`POST /api/v1/audit/{run_id}/resolutions`); `GET` returns the entries and a `chain_valid` flag.

## Consequences
- **Positive:** zero floating-point drift, reproducible run ids, and statute-anchored property tests (see `tests/test_hypothesis_statutory_fuzzing.py` and `tests/test_unseen_documents_and_regressions.py`). Throughput is reported by `benchmark.py` together with the hardware it was measured on.
- **Negative:** rate tables must be maintained by hand as notices are published; unknown periods raise rather than fall back.
- **Verification:** `pytest` (customs, drawback, freight, statutory fuzzing, provenance contract and unseen-document suites).
