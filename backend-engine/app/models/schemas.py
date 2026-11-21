from decimal import Decimal
from typing import Any, Dict, List, Literal, Optional

from pydantic import BaseModel, ConfigDict, EmailStr, Field, field_serializer, field_validator, model_validator


class BoundingBox(BaseModel):
    """
    Normalized bounding box coordinates in [0, 1000) space.
    x: distance from left border [0, 1000)
    y: distance from top border [0, 1000)
    width: box width [0, 1000)
    height: box height [0, 1000)
    page_number: 1-indexed document page
    confidence: element-wise extraction confidence [0.0, 1.0]
    """
    x: float = Field(..., ge=0.0, lt=1000.0, description="Normalized X coordinate [0, 1000)")
    y: float = Field(..., ge=0.0, lt=1000.0, description="Normalized Y coordinate [0, 1000)")
    width: float = Field(..., ge=0.0, le=1000.0, description="Normalized width [0, 1000)")
    height: float = Field(..., ge=0.0, le=1000.0, description="Normalized height [0, 1000)")
    page_number: int = Field(default=1, ge=1, description="1-based page number")
    confidence: float = Field(default=1.0, ge=0.0, le=1.0, description="Extraction confidence score [0.0, 1.0]")

    @field_validator("confidence")
    @classmethod
    def clamp_confidence(cls, v: float) -> float:
        return max(0.0, min(1.0, float(v)))

    @model_validator(mode="after")
    def validate_bounds(self) -> "BoundingBox":
        if self.x + self.width > 1000.0:
            raise ValueError(
                f"Bounding box extends beyond width limit: x ({self.x}) + width ({self.width}) = {self.x + self.width} > 1000.0"
            )
        if self.y + self.height > 1000.0:
            raise ValueError(
                f"Bounding box extends beyond height limit: y ({self.y}) + height ({self.height}) = {self.y + self.height} > 1000.0"
            )
        return self

class Discrepancy(BaseModel):
    """
    Audit discrepancy flag with statutory legal grounding, deterministic exposure amount,
    and visual bounding box overlay.
    """
    model_config = ConfigDict(from_attributes=True)

    id: str = Field(..., description="Unique discrepancy identifier")
    concept_id: str = Field(..., description="Concept key: concept_1_customs | concept_2_freight | concept_3_drawback")
    title: str = Field(..., description="Short executive title")
    description: str = Field(..., description="Detailed audit finding with statutory rationale")
    statutory_code: str = Field(..., description="Legal authority (e.g. 19 U.S.C. § 1592, 19 CFR § 152.103)")
    severity: str = Field(..., description="Severity level: critical | warning | info | opportunity")
    exposure_amount: Decimal = Field(..., description="Deterministic financial exposure or recovery in USD")
    confidence: float = Field(default=0.98, ge=0.0, le=1.0, description="Confidence of finding")
    bounding_box: BoundingBox = Field(..., description="Normalized document coordinates for visual highlighting")
    executive_summary: Optional[str] = Field(default=None, description="Plain English executive impact summary")
    financial_blast_radius: Optional[str] = Field(default=None, description="Direct calculation of financial exposure vs interest mitigation")
    statutory_defense: Optional[str] = Field(default=None, description="Recommended legal and architectural remediation protocol")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Additional structured parameters")

    @field_serializer("exposure_amount")
    def serialize_decimal(self, v: Decimal) -> str:
        return f"{v:.2f}"

class KillShotMetrics(BaseModel):
    """
    Executive Kill Shot metrics displayed in high-contrast crimson and emerald cards.
    """
    model_config = ConfigDict(from_attributes=True)

    penalty_exposure_avoided: Decimal = Field(default=Decimal("0.00"), description="19 U.S.C. § 1592 penalty exposure avoided")
    carrier_overbilling_caught: Decimal = Field(default=Decimal("0.00"), description="Carrier logistics overcharges intercepted")
    drawback_unclaimed_unlocked: Decimal = Field(default=Decimal("0.00"), description="Statutory 99% CBP duty refunds unlocked")

    @field_serializer("penalty_exposure_avoided", "carrier_overbilling_caught", "drawback_unclaimed_unlocked")
    def serialize_decimal(self, v: Decimal) -> str:
        return f"{v:.2f}"

def default_engagement_policy() -> Dict[str, Any]:
    """Default tenant policy snapshot (hashed into every run digest)."""
    return {
        "policy_id": "DEFAULT-FORWARDER-TIER-1",
        "auto_hold_threshold_usd": 10000.0,
        "commercial_freight_tolerance_usd": 25.0,
        "statutory_floor_enforced": True,
        "fmc_free_time_days": 4,
        "assist_amortization_method": "first_entry_lump_sum",
    }


class AuditResult(BaseModel):
    """
    Complete audit result payload for a specific concept, with immutable provenance
    and multi-tenant engagement policy snapshot per ADR-001 and ADR-004.
    """
    model_config = ConfigDict(from_attributes=True)

    concept_id: str
    title: str
    subtitle: str
    document_filename: str
    document_url: str
    metrics: KillShotMetrics
    discrepancies: List[Discrepancy]
    extracted_data: Dict[str, Any]
    offline_fallback_active: bool = False
    audit_run_id: str = Field(default="RUN-UNSET", description="Short form of run_digest")
    run_digest: Optional[str] = Field(
        default=None,
        description="SHA-256(calc_version | canonical(engagement_policy) | ruleset_hash | document_sha256) per ADR-001",
    )
    document_sha256: Optional[str] = Field(default=None, description="SHA-256 of the audited document bytes")
    ruleset_hash: Optional[str] = Field(default=None, description="SHA-256 of the rule-module sources")
    calc_version: str = Field(default="2026.2.0", description="Calculation kernel version")
    executed_at: Optional[str] = Field(default=None, description="ISO 8601 UTC execution timestamp")
    as_of_date: Optional[str] = Field(default=None, description="Date used for interest accrual and time limits")
    source: Literal["fixture", "upload", "custom_payload"] = Field(default="fixture", description="What was audited")
    missing_fields: List[str] = Field(default_factory=list, description="Required fields not found in the document")
    quarantine_reasons: List[str] = Field(default_factory=list, description="Why the release gate held the document")
    quarantine_status: Optional[str] = Field(default=None, description="QUARANTINED | RELEASED")
    engagement_policy: Dict[str, Any] = Field(
        default_factory=default_engagement_policy,
        description="Active tenant policy tolerances (strictly bounded by statutory floor)"
    )

class LeadCaptureRequest(BaseModel):
    """
    Validated lead capture request with strict email and length bounds.
    """
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    email: EmailStr = Field(..., description="Valid business email address")
    company_name: str = Field(..., min_length=2, max_length=120, description="Legal company name")
    phone: Optional[str] = Field(default=None, max_length=30, description="Contact phone number")
    monthly_import_volume: Optional[str] = Field(default=None, max_length=50, description="Estimated monthly container or entry volume")
    source: str = Field(default="conversion_modal", min_length=1, max_length=50, description="Lead acquisition source")
    privacy_consent: Literal[True] = Field(..., description="Explicit user privacy consent (must be true)")

class TelemetryEvent(BaseModel):
    """
    Validated telemetry event with bounded attributes and size constraints.
    """
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    event_type: str = Field(..., min_length=1, max_length=64, description="Telemetry event type identifier")
    concept_id: Optional[str] = Field(default=None, max_length=64, description="Associated concept identifier")
    discrepancy_id: Optional[str] = Field(default=None, max_length=64, description="Associated discrepancy identifier")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Event metadata attributes")

    @field_validator("metadata")
    @classmethod
    def validate_metadata(cls, v: Dict[str, Any]) -> Dict[str, Any]:
        if not isinstance(v, dict):
            raise ValueError("Telemetry metadata must be a dictionary")
        if len(v) > 50:
            raise ValueError("Telemetry metadata cannot exceed 50 key-value pairs")
        for k, val in v.items():
            if not isinstance(k, str) or len(k) > 64:
                raise ValueError("Telemetry metadata keys must be strings with length <= 64")
            if isinstance(val, str) and len(val) > 2000:
                raise ValueError("Telemetry metadata string values must have length <= 2000")
        return v
