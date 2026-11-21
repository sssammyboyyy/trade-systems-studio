/**
 * Records where the data on screen came from, so a fallback is never presented as live.
 *
 * - "live":     returned by the backend API
 * - "snapshot": backend output captured at build time (static demo, or backend unreachable)
 * - "client":   computed in the browser by the local PDF scanner
 */
import { useSyncExternalStore } from "react";
import type { DataSource } from "./types";

export interface DataSourceState {
  source: DataSource;
  /** Set when a backend was configured but a request failed. */
  error?: string;
  updatedAt: number;
}

let state: DataSourceState = { source: "snapshot", updatedAt: 0 };
const listeners = new Set<() => void>();

export function reportDataSource(source: DataSource, error?: string): void {
  state = { source, error, updatedAt: Date.now() };
  listeners.forEach((l) => l());
}

function subscribe(listener: () => void): () => void {
  listeners.add(listener);
  return () => listeners.delete(listener);
}

export function useDataSource(): DataSourceState {
  return useSyncExternalStore(subscribe, () => state, () => state);
}
