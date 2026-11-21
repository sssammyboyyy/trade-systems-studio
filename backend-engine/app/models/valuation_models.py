"""CBP Assist & Valuation Register Pydantic v2 Models (19 CFR § 152.103 & 19 U.S.C. § 1401a).

Enforces strict Python Decimal typing for statutory assist amortization, CIF/FOB freight deductions,
and 19 CFR § 162.74 Prior Disclosure penalty mitigation calculations.
"""

from decimal import Decimal
from enum import Enum
from typing import List

from pydantic import BaseModel, Field


class AssistCategory(str, Enum):
    TOOLING_DIES_MOLDS = "tooling_dies_molds"
    FOREIGN_ENGINEERING_DESIGN = "foreign_engineering_design"
    MATERIALS_CONSUMED = "materials_consumed"
    PRODUCTION_EQUIPMENT = "production_equipment"


class AmortizationMethod(str, Enum):
    FIRST_ENTRY = "first_entry"
    UNITS_PRODUCED = "units_produced"
    HISTORICAL_SCHEDULE = "historical_schedule"


class AssistItem(BaseModel):
    """An individual assist addition under 19 U.S.C. § 1401a(h)(1)(A)."""
    id: str
    description: str
    category: AssistCategory
    supplier_name: str
    country_of_origin: str
    total_acquisition_cost: Decimal
    anticipated_total_units: int = Field(..., gt=0)
    units_shipped_to_date: int = Field(0, ge=0)
    amortization_method: AmortizationMethod = AmortizationMethod.UNITS_PRODUCED
    is_declared_to_cbp: bool = False
    per_unit_amortized_cost: Decimal = Decimal("0.00")
    remaining_unamortized_cost: Decimal = Decimal("0.00")


class EntryValuationAudit(BaseModel):
    """Full valuation audit reconciling commercial invoice to statutory dutiable value."""
    entry_number: str
    importer_of_record: str
    declared_transaction_value: Decimal
    duty_rate_ad_valorem: Decimal
    invoice_incoterm: str = "CIF Los Angeles"
    international_freight_in_invoice: Decimal = Decimal("0.00")
    marine_insurance_in_invoice: Decimal = Decimal("0.00")
    improper_cif_overvaluation: Decimal = Decimal("0.00")
    assists_omitted_cost: Decimal = Decimal("0.00")
    adjusted_lawful_dutiable_value: Decimal
    lawful_duty_due: Decimal
    declared_duty_paid: Decimal
    duty_underpayment: Decimal
    statutory_interest_19usc1505: Decimal
    negligence_penalty_exposure: Decimal = Field(..., description="Statutory maximum, 19 U.S.C. 1592(c)(3): 2x loss of duty (or lesser domestic value)")
    gross_negligence_penalty_exposure: Decimal = Field(..., description="Statutory maximum, 19 U.S.C. 1592(c)(2): 4x loss of duty (or lesser domestic value)")
    prior_disclosure_tender_amount: Decimal = Field(..., description="Loss of duty plus interest tendered with a prior disclosure (19 CFR 162.74)")
    total_liability_avoided: Decimal = Field(..., description="Negligence maximum minus the post-disclosure penalty (interest)")
    assists_audited: List[AssistItem] = Field(default_factory=list)


class PriorDisclosurePackage(BaseModel):
    """Statutory Prior Disclosure filing packet under 19 CFR § 162.74."""
    filing_reference_id: str
    port_of_entry: str
    addressed_to: str
    statutory_statutes_cited: List[str]
    narrative_explanation: str
    affected_entries: List[str]
    actual_duty_loss: Decimal
    interest_tender_amount: Decimal
    total_tender_check: Decimal
    letter_text: str

    @property
    def statutory_letter_body(self) -> str:
        return self.letter_text
