export interface BoundingBox {
  x: number; // [0, 1000)
  y: number; // [0, 1000)
  width: number; // [0, 1000)
  height: number; // [0, 1000)
  page_number: number;
  confidence: number;
}

export interface Discrepancy {
  id: string;
  concept_id: string;
  title: string;
  description: string;
  statutory_code: string;
  severity: "critical" | "warning" | "info" | "opportunity";
  exposure_amount: string | number;
  confidence: number;
  bounding_box: BoundingBox;
  executive_summary?: string;
  financial_blast_radius?: string;
  statutory_defense?: string;
  metadata?: Record<string, any>;
}

export interface KillShotMetrics {
  penalty_exposure_avoided: string | number;
  carrier_overbilling_caught: string | number;
  drawback_unclaimed_unlocked: string | number;
}

export interface EngagementPolicy {
  policy_id: string;
  auto_hold_threshold_usd: string | number;
  commercial_freight_tolerance_usd: string | number;
  statutory_floor_enforced: boolean;
  fmc_free_time_days: number;
  assist_amortization_method: string;
}

export type ResolutionActionType = "approve_clean" | "request_paperwork" | "escalate_broker";

export interface ResolutionRecord {
  discrepancy_id: string;
  action: ResolutionActionType;
  reason_code: string;
  notes?: string;
  timestamp: string;
  resolved_by: string;
}

export interface AuditResult {
  concept_id: string;
  title: string;
  subtitle: string;
  document_filename: string;
  document_url: string;
  metrics: KillShotMetrics;
  discrepancies: Discrepancy[];
  extracted_data: Record<string, any>;
  offline_fallback_active?: boolean;
  audit_run_id?: string;
  /** SHA-256(calc_version | policy | ruleset_hash | document_sha256), per ADR-001 */
  run_digest?: string | null;
  /** SHA-256 of the audited document bytes, computed by the backend */
  document_sha256?: string | null;
  ruleset_hash?: string | null;
  calc_version?: string;
  executed_at?: string;
  as_of_date?: string | null;
  source?: "fixture" | "upload" | "custom_payload" | "client";
  missing_fields?: string[];
  quarantine_reasons?: string[];
  quarantine_status?: "QUARANTINED" | "RELEASED" | "ESCALATED" | null;
  engagement_policy?: EngagementPolicy | Record<string, any>;
}

/** Where a piece of data came from, so the UI never presents a fallback as live. */
export type DataSource = "live" | "snapshot" | "client";

export interface Sourced<T> {
  data: T;
  source: DataSource;
  error?: string;
}

export interface CargoWiseDiff {
  concept_id: string;
  audit_run_id: string;
  status: "READY_FOR_INGESTION" | "HELD_PENDING_REVIEW" | "BLOCKED_DO_NOT_TRANSMIT" | "NOT_APPLICABLE";
  schema_version: string;
  schema_validation: string;
  raw_unaudited_xml: string;
  reconciled_lawful_xml: string;
  diff_summary: Array<{ node: string; raw: string; reconciled: string; statute: string; status: string }>;
}

export type LedgerAction = "APPROVE" | "REQUEST_DOCS" | "ESCALATE" | "OVERRIDE_HTS" | "REOPEN";

export interface LedgerEntry {
  seq: number;
  run_id: string;
  finding_id: string;
  action: LedgerAction;
  reason: string;
  actor: string;
  override_value?: string | null;
  ts: string;
  prev_hash: string;
  hash: string;
}

export interface LeadCapturePayload {
  email: string;
  company_name: string;
  phone?: string;
  monthly_import_volume?: string;
  source?: string;
  privacy_consent: boolean;
}

export interface TelemetryPayload {
  event_type: string;
  concept_id?: string;
  discrepancy_id?: string;
  metadata?: Record<string, any>;
}

export interface GraphNode {
  id: string;
  label: string;
  country: string;
  is_blocked: boolean;
  risk_level: "SDN_BLOCKED" | "HIGH_RISK_SHELL" | "CLEAN_COMMERCIAL" | "PEP" | "EAR_EXPORT_RESTRICTION" | "COMPLIANCE_HOLD" | string;
  programs: string[];
  sanction_authority?: string;
  notes?: string;
}

export interface GraphEdge {
  source_id: string;
  target_id: string;
  ownership_pct: number;
  relationship_type: string;
}

export interface OFAC50PercentEvaluation {
  target_entity_id: string;
  target_entity_name: string;
  total_blocked_ownership_pct: number;
  is_blocked_by_50_percent_rule: boolean;
  direct_sdn_status: boolean;
  statutory_citation: string;
  blocking_entities: Array<{
    owner_id: string;
    owner_name: string;
    country: string;
    ownership_pct: number;
    programs: string[];
  }>;
  compliance_action:
    | "BLOCK_AND_REPORT"
    | "ENHANCED_DUE_DILIGENCE"
    | "CLEAR_TRANSACTION"
    | "LICENSE_REQUIRED_EAR"
    | "REQUIRES_MANUAL_REVIEW";
}

export interface CorporateGraphResponse {
  target_id: string;
  nodes: GraphNode[];
  edges: GraphEdge[];
  evaluation: OFAC50PercentEvaluation;
}

// -------------------------------------------------------------
// Pillar 3: HTS Classification Copilot Types
// -------------------------------------------------------------
export interface GRIDecisionNode {
  step_rule: string;
  heading_or_subheading: string;
  description: string;
  legal_rationale: string;
  confidence: number;
  passed: boolean;
  competing_candidates: string[];
}

export interface LandedCostBreakdown {
  entered_value: string | number;
  duty_rate_ad_valorem: string | number;
  customs_duty: string | number;
  section_301_rate?: string | number;
  section_301_duty?: string | number;
  section_301_subheading?: string;
  mpf_rate: string | number;
  mpf_min_cap: string | number;
  mpf_max_cap: string | number;
  mpf_fee: string | number;
  hmf_rate: string | number;
  hmf_fee: string | number;
  freight_and_insurance: string | number;
  total_customs_cost: string | number;
  total_landed_cost: string | number;
  fiscal_year?: string;
}

export interface HTSClassificationResult {
  item_id: string;
  product_title: string;
  input_description: string;
  country_of_origin: string;
  declared_hts_code?: string;
  classified_hts_code: string;
  confidence: number;
  requires_human_review: boolean;
  gri_path: GRIDecisionNode[];
  chapter_notes_cited: string[];
  landed_cost: LandedCostBreakdown;
}

// -------------------------------------------------------------
// Pillar 4: CBP Assist & Valuation Register Types
// -------------------------------------------------------------
export type AssistCategory =
  | "tooling_dies_molds"
  | "foreign_engineering_design"
  | "materials_consumed"
  | "production_equipment";

export type AmortizationMethod =
  | "first_entry"
  | "units_produced"
  | "historical_schedule";

export interface AssistItem {
  id: string;
  description: string;
  category: AssistCategory;
  supplier_name: string;
  country_of_origin: string;
  total_acquisition_cost: string | number;
  anticipated_total_units: number;
  units_shipped_to_date: number;
  amortization_method: AmortizationMethod;
  is_declared_to_cbp: boolean;
  per_unit_amortized_cost: string | number;
  remaining_unamortized_cost: string | number;
}

export interface EntryValuationAudit {
  entry_number: string;
  importer_of_record: string;
  declared_transaction_value: string | number;
  duty_rate_ad_valorem: string | number;
  invoice_incoterm: string;
  international_freight_in_invoice: string | number;
  marine_insurance_in_invoice: string | number;
  improper_cif_overvaluation: string | number;
  assists_omitted_cost: string | number;
  adjusted_lawful_dutiable_value: string | number;
  lawful_duty_due: string | number;
  declared_duty_paid: string | number;
  duty_underpayment: string | number;
  statutory_interest_19usc1505: string | number;
  negligence_penalty_exposure: string | number;
  gross_negligence_penalty_exposure: string | number;
  prior_disclosure_tender_amount: string | number;
  total_liability_avoided: string | number;
  assists_audited: AssistItem[];
}

export interface PriorDisclosurePackage {
  filing_reference_id: string;
  port_of_entry: string;
  addressed_to: string;
  statutory_statutes_cited: string[];
  narrative_explanation: string;
  affected_entries: string[];
  actual_duty_loss: string | number;
  interest_tender_amount: string | number;
  total_tender_check: string | number;
  letter_text: string;
}
