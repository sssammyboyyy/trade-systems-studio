/**
 * Offline dataset for the static demo.
 *
 * Every value here is produced by the backend engines on the bundled fixture PDFs
 * (scripts/export_frontend_snapshot.py) and checked for staleness in CI. Nothing in
 * this file is hand-typed, so the offline demo cannot drift from the backend.
 */
import snapshot from "./generated/backend-snapshot.json";
import {
  AuditResult,
  KillShotMetrics,
  CorporateGraphResponse,
  HTSClassificationResult,
  AssistItem,
  EntryValuationAudit,
  PriorDisclosurePackage,
  CargoWiseDiff,
} from "@/lib/types";

const s = snapshot as unknown as {
  as_of_date: string;
  aggregate_metrics: KillShotMetrics;
  audits: Record<string, AuditResult>;
  cargowise: Record<string, CargoWiseDiff>;
  sanctions_graphs: Record<string, CorporateGraphResponse>;
  hts_presets: Record<string, HTSClassificationResult>;
  assist_items: AssistItem[];
  valuation_audit: EntryValuationAudit;
  prior_disclosure: PriorDisclosurePackage;
};

export const SNAPSHOT_AS_OF: string = s.as_of_date;
export const AGGREGATE_METRICS: KillShotMetrics = s.aggregate_metrics;
export const MOCK_AUDIT_DATA: Record<string, AuditResult> = s.audits;
export const INITIAL_CUSTOMS_NIGHTMARE_FIXTURE: AuditResult = s.audits["concept_1_customs"];
export const MOCK_CARGOWISE_DIFFS: Record<string, CargoWiseDiff> = s.cargowise;
export const MOCK_SANCTIONS_GRAPHS: Record<string, CorporateGraphResponse> = s.sanctions_graphs;
export const MOCK_HTS_PRESETS: Record<string, HTSClassificationResult> = s.hts_presets;
export const MOCK_ASSIST_ITEMS: AssistItem[] = s.assist_items;
export const MOCK_VALUATION_AUDIT: EntryValuationAudit = s.valuation_audit;
export const MOCK_PRIOR_DISCLOSURE: PriorDisclosurePackage = s.prior_disclosure;
