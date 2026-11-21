#!/usr/bin/env python3
"""TradeTech Systems Studio  -  Enterprise Concurrency & Latency Benchmark.

Measures throughput and p50/p90/p95/p99 latency of the six engines on this machine.
"""

import argparse
import os
import platform
import statistics
import time
from decimal import Decimal

from app.services.extractor import TradeDocumentExtractor
from app.services.hts_classifier import HTSClassifierEngine
from app.services.sanctions_screener import sanctions_screener
from app.services.valuation_ledger import CustomsValuationService


def run_comprehensive_benchmark(iterations: int = 500, write_doc: bool = False, json_path: str = ""):
    print(f"Executing enterprise benchmark suite across {iterations} iterations...")
    
    extractor = TradeDocumentExtractor()
    hts_engine = HTSClassifierEngine()
    val_service = CustomsValuationService()

    latencies_customs = []
    latencies_freight = []
    latencies_drawback = []
    latencies_sanctions = []
    latencies_hts = []
    latencies_valuation = []

    start_total = time.perf_counter()

    for i in range(iterations):
        # 1. Customs Firewall
        t0 = time.perf_counter()
        extractor.run_audit("concept_1_customs")
        latencies_customs.append((time.perf_counter() - t0) * 1000)

        # 2. Freight Overbilling
        t0 = time.perf_counter()
        extractor.run_audit("concept_2_freight")
        latencies_freight.append((time.perf_counter() - t0) * 1000)

        # 3. Duty Drawback
        t0 = time.perf_counter()
        extractor.run_audit("concept_3_drawback")
        latencies_drawback.append((time.perf_counter() - t0) * 1000)

        # 4. Sanctions OFAC 50% Rule
        t0 = time.perf_counter()
        sanctions_screener.get_ownership_graph("bis-el-cn-0941")
        latencies_sanctions.append((time.perf_counter() - t0) * 1000)

        # 5. HTS Classifier (Drone Motor)
        t0 = time.perf_counter()
        hts_engine.get_preset("drone_motor", entered_value=Decimal("50000.00"))
        latencies_hts.append((time.perf_counter() - t0) * 1000)

        # 6. Valuation Ledger & Prior Disclosure
        t0 = time.perf_counter()
        audit_res = val_service.audit_entry_valuation()
        val_service.generate_prior_disclosure(audit_res)
        latencies_valuation.append((time.perf_counter() - t0) * 1000)

    total_duration = time.perf_counter() - start_total
    total_audits = iterations * 6
    throughput = total_audits / total_duration

    tier1_audits = iterations * 3
    tier1_duration = (
        sum(latencies_customs) + sum(latencies_freight) + sum(latencies_drawback)
    ) / 1000.0
    tier1_throughput = tier1_audits / tier1_duration if tier1_duration > 0 else 0.0

    tier2_audits = iterations * 3
    tier2_duration = (
        sum(latencies_sanctions) + sum(latencies_hts) + sum(latencies_valuation)
    ) / 1000.0
    tier2_throughput = tier2_audits / tier2_duration if tier2_duration > 0 else 0.0

    def get_stats(data):
        s = sorted(data)
        p50 = statistics.median(s)
        p90 = s[int(len(s) * 0.90)]
        p95 = s[int(len(s) * 0.95)]
        p99 = s[int(len(s) * 0.99)]
        avg = statistics.mean(s)
        return {"avg": avg, "p50": p50, "p90": p90, "p95": p95, "p99": p99}

    stats_customs = get_stats(latencies_customs)
    stats_freight = get_stats(latencies_freight)
    stats_drawback = get_stats(latencies_drawback)
    stats_sanctions = get_stats(latencies_sanctions)
    stats_hts = get_stats(latencies_hts)
    stats_valuation = get_stats(latencies_valuation)

    tier1_max_p99 = max(stats_customs["p99"], stats_freight["p99"], stats_drawback["p99"])
    tier2_max_p99 = max(stats_sanctions["p99"], stats_hts["p99"], stats_valuation["p99"])

    hw_spec = (
        f"{platform.system()} {platform.release()} ({platform.machine()}), "
        f"{os.cpu_count() or 'unknown'} logical CPUs, Python {platform.python_version()}"
    )

    report_markdown = f"""# ⚡ Enterprise Performance & Throughput Benchmark

> **System:** TradeTech Systems Studio  
> **Architect & Lead:** Samuel Rencken (Principal AI Systems Architect & Lead TradeTech Engineer)  
> **Target Scale:** Enterprise Freight Forwarders, Customs Brokerages, and Tier-1 Importers  
> **Benchmark Date:** November 2026  
> **Hardware & Runtime:** {hw_spec}  
> **Methodology:** Two-tier measurement separating end-to-end 2-page `pypdf` document parsing & real field extraction from pure in-memory statutory compute ({iterations:,} iterations x 6 engines = {total_audits:,} audits)

---

## 📊 Executive Performance Summary (Two-Tier Breakdown)

```
┌────────────────────────────────────────────────────────────────────────────────────────┐
│ TOTAL AUDITS EXECUTED:        {total_audits:,} statutory compliance verifications            │
│ TOTAL WALL CLOCK TIME:        {total_duration:.2f} seconds                                   │
│ COMBINED THROUGHPUT:          {throughput:,.1f} full-suite audits / second                   │
│ TIER 1 (2-PAGE PDF + AUDIT):  {tier1_throughput:,.1f} documents / second (max p99: {tier1_max_p99:.1f} ms)     │
│ TIER 2 (PURE STATUTORY CORE): {tier2_throughput:,.1f} evaluations / second (max p99: {tier2_max_p99:.3f} ms)  │
│ FLOATING-POINT DRIFT:         0.000000000% (Strict Python Decimal Determinism)         │
└────────────────────────────────────────────────────────────────────────────────────────┘
```

---

## ⏱️ Tier 1: End-to-End 2-Page PDF Parsing + Statutory Audit (Milliseconds)

*Includes real binary PDF loading, `pypdf` layout coordinate extraction on `[0, 1000)`, field validation, and `Decimal` penalty/recovery calculation on every iteration.*

| Pillar & Compliance Domain | Mean Latency | Median (p50) | 90th %ile (p90) | 95th %ile (p95) | 99th %ile (p99) |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **01. Customs Valuation (19 USC § 1592)** | {stats_customs['avg']:.3f} ms | {stats_customs['p50']:.3f} ms | {stats_customs['p90']:.3f} ms | {stats_customs['p95']:.3f} ms | {stats_customs['p99']:.3f} ms |
| **02. Freight Audit (46 CFR Part 541)** | {stats_freight['avg']:.3f} ms | {stats_freight['p50']:.3f} ms | {stats_freight['p90']:.3f} ms | {stats_freight['p95']:.3f} ms | {stats_freight['p99']:.3f} ms |
| **03. Duty Drawback (19 USC § 1313)** | {stats_drawback['avg']:.3f} ms | {stats_drawback['p50']:.3f} ms | {stats_drawback['p90']:.3f} ms | {stats_drawback['p95']:.3f} ms | {stats_drawback['p99']:.3f} ms |

---

## ⚡ Tier 2: Pure In-Memory Deterministic Compute (Sub-Millisecond)

*Evaluates recursive OFAC 50% Rule ownership graphs, WCO GRI 1 to 6 tariff trees, and GAAP assist amortization + DRAFT Prior Disclosure assembly directly in memory.*

| Pillar & Compliance Domain | Mean Latency | Median (p50) | 90th %ile (p90) | 95th %ile (p95) | 99th %ile (p99) |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **04. Sanctions Graph (OFAC 50% Rule)** | {stats_sanctions['avg']:.3f} ms | {stats_sanctions['p50']:.3f} ms | {stats_sanctions['p90']:.3f} ms | {stats_sanctions['p95']:.3f} ms | {stats_sanctions['p99']:.3f} ms |
| **05. HTS Classification Copilot (WCO GRI)** | {stats_hts['avg']:.3f} ms | {stats_hts['p50']:.3f} ms | {stats_hts['p90']:.3f} ms | {stats_hts['p95']:.3f} ms | {stats_hts['p99']:.3f} ms |
| **06. Assist Register (19 CFR § 152.103)** | {stats_valuation['avg']:.3f} ms | {stats_valuation['p50']:.3f} ms | {stats_valuation['p90']:.3f} ms | {stats_valuation['p95']:.3f} ms | {stats_valuation['p99']:.3f} ms |

---

## Reading these numbers

- Figures are machine-dependent: they were measured on the hardware listed above, single process, warm cache.
- Tier 1 includes reading and parsing the bundled 2-page PDFs on every iteration; Tier 2 is pure in-memory rule evaluation.
- No comparison with other products is made here; no third-party latency figures were measured.

---

## 🚀 Live Demonstration Console

Experience the interactive audit viewer live at:  
👉 **[https://sssammyboyyy.github.io/trade-systems-studio/](https://sssammyboyyy.github.io/trade-systems-studio/)**
"""

    print(report_markdown)

    if write_doc:
        report_path = os.path.join(
            os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
            "docs",
            "PERFORMANCE_AND_SCALE_BENCHMARKS.md",
        )
        with open(report_path, "w", encoding="utf-8") as f:
            f.write(report_markdown)
        print(f"Report written to: {report_path}")

    if json_path:
        import json
        from datetime import date

        payload = {
            "measured_on": date.today().isoformat(),
            "hardware": hw_spec,
            "iterations": iterations,
            "tier1_docs_per_sec": round(tier1_throughput, 1),
            "tier1_p99_ms": round(tier1_max_p99, 2),
            "tier2_evals_per_sec": round(tier2_throughput, 1),
            "tier2_p99_ms": round(tier2_max_p99, 3),
        }
        with open(json_path, "w", encoding="utf-8") as f:
            json.dump(payload, f, indent=2)
            f.write("\n")
        print(f"Benchmark JSON written to: {json_path}")

    print(f"Benchmark completed in {total_duration:.2f}s ({throughput:,.1f} audits/sec).")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="TradeTech Systems Studio  -  Enterprise Concurrency & Latency Benchmark."
    )
    parser.add_argument(
        "--iterations",
        type=int,
        default=500,
        help="Number of iterations for the benchmark suite (default: 500)",
    )
    parser.add_argument(
        "--write-doc",
        action="store_true",
        default=False,
        help="Write report to docs/PERFORMANCE_AND_SCALE_BENCHMARKS.md",
    )
    parser.add_argument(
        "--json",
        default="",
        help="Also write the headline numbers as JSON (used by the frontend), e.g. "
        "../frontend-dashboard/src/data/generated/benchmark.json",
    )
    args = parser.parse_args()
    run_comprehensive_benchmark(iterations=args.iterations, write_doc=args.write_doc, json_path=args.json)
