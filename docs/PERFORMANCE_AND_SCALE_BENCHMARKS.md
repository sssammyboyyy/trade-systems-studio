# ⚡ Enterprise Performance & Throughput Benchmark

> **System:** TradeTech Systems Studio  
> **Architect & Lead:** Samuel Rencken (Principal AI Systems Architect & Lead TradeTech Engineer)  
> **Target Scale:** Enterprise Freight Forwarders, Customs Brokerages, and Tier-1 Importers  
> **Benchmark Date:** November 2026  
> **Hardware & Runtime:** Darwin 27.0.0 (arm64), 10 logical CPUs, Python 3.11.15  
> **Methodology:** Two-tier measurement separating end-to-end 2-page `pypdf` document parsing & real field extraction from pure in-memory statutory compute (300 iterations x 6 engines = 1,800 audits)

---

## 📊 Executive Performance Summary (Two-Tier Breakdown)

```
┌────────────────────────────────────────────────────────────────────────────────────────┐
│ TOTAL AUDITS EXECUTED:        1,800 statutory compliance verifications            │
│ TOTAL WALL CLOCK TIME:        8.32 seconds                                   │
│ COMBINED THROUGHPUT:          216.4 full-suite audits / second                   │
│ TIER 1 (2-PAGE PDF + AUDIT):  108.5 documents / second (max p99: 16.2 ms)     │
│ TIER 2 (PURE STATUTORY CORE): 35,069.5 evaluations / second (max p99: 0.049 ms)  │
│ FLOATING-POINT DRIFT:         0.000000000% (Strict Python Decimal Determinism)         │
└────────────────────────────────────────────────────────────────────────────────────────┘
```

---

## ⏱️ Tier 1: End-to-End 2-Page PDF Parsing + Statutory Audit (Milliseconds)

*Includes real binary PDF loading, `pypdf` layout coordinate extraction on `[0, 1000)`, field validation, and `Decimal` penalty/recovery calculation on every iteration.*

| Pillar & Compliance Domain | Mean Latency | Median (p50) | 90th %ile (p90) | 95th %ile (p95) | 99th %ile (p99) |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **01. Customs Valuation (19 USC § 1592)** | 9.923 ms | 9.896 ms | 10.006 ms | 10.059 ms | 10.796 ms |
| **02. Freight Audit (46 CFR Part 541)** | 10.323 ms | 9.799 ms | 10.297 ms | 15.642 ms | 16.167 ms |
| **03. Duty Drawback (19 USC § 1313)** | 7.393 ms | 7.382 ms | 7.477 ms | 7.552 ms | 7.907 ms |

---

## ⚡ Tier 2: Pure In-Memory Deterministic Compute (Sub-Millisecond)

*Evaluates recursive OFAC 50% Rule ownership graphs, WCO GRI 1 to 6 tariff trees, and GAAP assist amortization + DRAFT Prior Disclosure assembly directly in memory.*

| Pillar & Compliance Domain | Mean Latency | Median (p50) | 90th %ile (p90) | 95th %ile (p95) | 99th %ile (p99) |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **04. Sanctions Graph (OFAC 50% Rule)** | 0.021 ms | 0.020 ms | 0.026 ms | 0.027 ms | 0.035 ms |
| **05. HTS Classification Copilot (WCO GRI)** | 0.031 ms | 0.028 ms | 0.035 ms | 0.037 ms | 0.042 ms |
| **06. Assist Register (19 CFR § 152.103)** | 0.034 ms | 0.032 ms | 0.041 ms | 0.043 ms | 0.049 ms |

---

## Reading these numbers

- Figures are machine-dependent: they were measured on the hardware listed above, single process, warm cache.
- Tier 1 includes reading and parsing the bundled 2-page PDFs on every iteration; Tier 2 is pure in-memory rule evaluation.
- No comparison with other products is made here; no third-party latency figures were measured.

---

## 🚀 Live Demonstration Console

Experience the interactive audit viewer live at:  
👉 **[https://sssammyboyyy.github.io/trade-systems-studio/](https://sssammyboyyy.github.io/trade-systems-studio/)**
