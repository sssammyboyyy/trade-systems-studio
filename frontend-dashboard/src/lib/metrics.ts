/**
 * Single source of truth for every number the UI quotes about the system itself.
 *
 * - VERIFIED_PYTEST_COUNT is kept in sync with `pytest --collect-only` by
 *   scripts/sync_metrics.py (CI fails on drift).
 * - BENCHMARK is written by `python benchmark.py --json ...` and states the hardware it
 *   was measured on, because throughput is machine-dependent.
 */
import benchmark from "@/data/generated/benchmark.json";

export const VERIFIED_PYTEST_COUNT = 260;

export const BENCHMARK = benchmark as {
  measured_on: string;
  hardware: string;
  iterations: number;
  tier1_docs_per_sec: number;
  tier1_p99_ms: number;
  tier2_evals_per_sec: number;
  tier2_p99_ms: number;
};

export const fmtRate = (n: number) => Math.round(n).toLocaleString("en-US");
