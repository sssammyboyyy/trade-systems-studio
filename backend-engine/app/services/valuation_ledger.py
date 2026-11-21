"""CBP Valuation & Assist Ledger Service.

Calculates statutory additions to transaction value (19 U.S.C. § 1401a), GAAP assist
amortization under 19 CFR § 152.103, and automated 19 CFR § 162.74 Prior Disclosure
penalty mitigation filings using strict Python Decimal.
"""

from datetime import datetime, timezone
from decimal import ROUND_HALF_UP, Decimal
from typing import List, Optional

from app.core.penalties import max_1592_penalty, prior_disclosure_penalty
from app.models.valuation_models import (
    AmortizationMethod,
    AssistCategory,
    AssistItem,
    EntryValuationAudit,
    PriorDisclosurePackage,
)

# Planning rate for 19 U.S.C. 1505 interest when no entry date is supplied
STATUTORY_INTEREST_RATE = Decimal("0.0700")


class CustomsValuationService:
    """Enterprise customs valuation, assist amortization, and statutory prior disclosure generator."""

    DEFAULT_ASSISTS: List[AssistItem] = [
        AssistItem(
            id="AST-2026-001",
            description="Multi-Cavity Liquid Silicone Injection Tooling & Molds",
            category=AssistCategory.TOOLING_DIES_MOLDS,
            supplier_name="Dongguan Precision Tooling Co., Ltd.",
            country_of_origin="CN",
            total_acquisition_cost=Decimal("185000.00"),
            anticipated_total_units=100000,
            units_shipped_to_date=15000,
            amortization_method=AmortizationMethod.UNITS_PRODUCED,
            is_declared_to_cbp=False,
            per_unit_amortized_cost=Decimal("1.85"),
            remaining_unamortized_cost=Decimal("157250.00"),
        ),
        AssistItem(
            id="AST-2026-002",
            description="Custom ASIC Firmware & Overseas PCB Micro-Architecture Layout",
            category=AssistCategory.FOREIGN_ENGINEERING_DESIGN,
            supplier_name="Kyoto Micro-Embedded Labs",
            country_of_origin="JP",
            total_acquisition_cost=Decimal("120000.00"),
            anticipated_total_units=60000,
            units_shipped_to_date=10000,
            amortization_method=AmortizationMethod.UNITS_PRODUCED,
            is_declared_to_cbp=False,
            per_unit_amortized_cost=Decimal("2.00"),
            remaining_unamortized_cost=Decimal("100000.00"),
        ),
        AssistItem(
            id="AST-2026-003",
            description="Specialized CNC Milling Fixtures & Progressive Stamping Dies",
            category=AssistCategory.TOOLING_DIES_MOLDS,
            supplier_name="Bavaria Precision Machining GmbH",
            country_of_origin="DE",
            total_acquisition_cost=Decimal("95000.00"),
            anticipated_total_units=50000,
            units_shipped_to_date=50000,
            amortization_method=AmortizationMethod.FIRST_ENTRY,
            is_declared_to_cbp=True,
            per_unit_amortized_cost=Decimal("1.90"),
            remaining_unamortized_cost=Decimal("0.00"),
        ),
    ]

    def audit_entry_valuation(
        self,
        entry_number: str = "CBP-7501-84920184",
        importer_of_record: str = "Pacific Tech Imports LLC (EIN 94-8291048)",
        declared_transaction_value: Decimal = Decimal("450000.00"),
        duty_rate_ad_valorem: Decimal = Decimal("0.054"),  # 5.4%
        current_entry_units: int = 15000,
        invoice_incoterm: str = "CIF Los Angeles",
        international_freight_in_invoice: Decimal = Decimal("24500.00"),
        marine_insurance_in_invoice: Decimal = Decimal("3200.00"),
        assists: Optional[List[AssistItem]] = None,
        months_elapsed: int = 9,
    ) -> EntryValuationAudit:
        """Perform statutory valuation audit under 19 U.S.C. § 1401a and 19 CFR § 152.103."""
        if assists is None:
            assists = [a.model_copy() for a in self.DEFAULT_ASSISTS]

        # 1. Identify CIF deduction errors (International freight & marine insurance are non-dutiable)
        improper_cif_overvaluation = Decimal("0.00")
        if "CIF" in invoice_incoterm.upper():
            improper_cif_overvaluation = (international_freight_in_invoice + marine_insurance_in_invoice).quantize(
                Decimal("0.01"), rounding=ROUND_HALF_UP
            )

        # 2. Identify Undeclared Assists (Statutory additions to value)
        assists_omitted_cost = Decimal("0.00")
        updated_assists = []

        for assist in assists:
            if assist.anticipated_total_units > 0:
                per_unit = (assist.total_acquisition_cost / Decimal(assist.anticipated_total_units)).quantize(
                    Decimal("0.0001"), rounding=ROUND_HALF_UP
                )
            else:
                per_unit = Decimal("0.00")

            if assist.amortization_method == AmortizationMethod.FIRST_ENTRY:
                allocated = assist.total_acquisition_cost if assist.units_shipped_to_date == 0 else Decimal("0.00")
            else:
                allocated = (per_unit * Decimal(current_entry_units)).quantize(
                    Decimal("0.01"), rounding=ROUND_HALF_UP
                )

            # Check if undeclared
            if not assist.is_declared_to_cbp:
                assists_omitted_cost += allocated

            assist_copy = assist.model_copy(
                update={
                    "per_unit_amortized_cost": per_unit.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP),
                }
            )
            updated_assists.append(assist_copy)

        # 3. Calculate Lawful Dutiable Value:
        # Lawful Value = Declared Value - Improper CIF Additions + Undeclared Assists
        adjusted_lawful_dutiable_value = (
            declared_transaction_value - improper_cif_overvaluation + assists_omitted_cost
        ).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)

        # 4. Duty Calculations
        declared_duty_paid = (declared_transaction_value * duty_rate_ad_valorem).quantize(
            Decimal("0.01"), rounding=ROUND_HALF_UP
        )
        lawful_duty_due = (adjusted_lawful_dutiable_value * duty_rate_ad_valorem).quantize(
            Decimal("0.01"), rounding=ROUND_HALF_UP
        )

        duty_underpayment = max(Decimal("0.00"), (lawful_duty_due - declared_duty_paid).quantize(
            Decimal("0.01"), rounding=ROUND_HALF_UP
        ))

        # 5. Statutory Interest under 19 U.S.C. § 1505(c) & 26 U.S.C. §§ 6621/6622
        # Statutory interest is compounded daily at quarterly benchmark rates
        from app.core.statutory_rates import calculate_1505_interest_by_months
        interest_owed = calculate_1505_interest_by_months(duty_underpayment, months_elapsed=months_elapsed)

        # 6. 19 U.S.C. 1592(c) statutory maximums (no domestic value supplied, so no cap applied)
        negligence_penalty = max_1592_penalty("negligence", duty_underpayment, adjusted_lawful_dutiable_value) or Decimal("0.00")
        gross_negligence_penalty = (
            max_1592_penalty("gross_negligence", duty_underpayment, adjusted_lawful_dutiable_value) or Decimal("0.00")
        )

        # 7. Prior disclosure (19 CFR 162.74, 1592(c)(4)(B)): for negligence the penalty is
        # limited to interest; the loss of duty must also be tendered.
        pd_penalty = prior_disclosure_penalty("negligence", duty_underpayment, interest_owed) or Decimal("0.00")
        prior_disclosure_tender = duty_underpayment + pd_penalty
        total_liability_avoided = max(Decimal("0.00"), negligence_penalty - pd_penalty)

        return EntryValuationAudit(
            entry_number=entry_number,
            importer_of_record=importer_of_record,
            declared_transaction_value=declared_transaction_value,
            duty_rate_ad_valorem=duty_rate_ad_valorem,
            invoice_incoterm=invoice_incoterm,
            international_freight_in_invoice=international_freight_in_invoice,
            marine_insurance_in_invoice=marine_insurance_in_invoice,
            improper_cif_overvaluation=improper_cif_overvaluation,
            assists_omitted_cost=assists_omitted_cost,
            adjusted_lawful_dutiable_value=adjusted_lawful_dutiable_value,
            lawful_duty_due=lawful_duty_due,
            declared_duty_paid=declared_duty_paid,
            duty_underpayment=duty_underpayment,
            statutory_interest_19usc1505=interest_owed,
            negligence_penalty_exposure=negligence_penalty,
            gross_negligence_penalty_exposure=gross_negligence_penalty,
            prior_disclosure_tender_amount=prior_disclosure_tender,
            total_liability_avoided=total_liability_avoided,
            assists_audited=updated_assists,
        )

    def generate_prior_disclosure(
        self,
        audit: EntryValuationAudit,
        port_of_entry: str = "Los Angeles / Long Beach (2704)",
        as_of: Optional[datetime] = None,
    ) -> PriorDisclosurePackage:
        """Draft a prior disclosure under 19 CFR 162.74 (for review by a licensed broker or counsel)."""
        when = as_of or datetime.now(timezone.utc)
        now_str = when.strftime("%B %d, %Y")
        ref_id = f"PD-{audit.entry_number[-8:]}-{when.strftime('%Y%m%d')}"

        letter_text = f"""*** DRAFT -- GENERATED BY TradeTech Systems Studio Compliance Automation Engine FOR REVIEW BY LICENSED CUSTOMS BROKER OR LEGAL COUNSEL ***

FORMAL PRIOR DISCLOSURE UNDER 19 CFR § 162.74
AND 19 U.S.C. § 1592(c)(4)

DATE: {now_str}
REFERENCE: {ref_id}

TO:
Port Director, U.S. Customs and Border Protection
Fines, Penalties, and Forfeitures Officer
Port of {port_of_entry}

FROM:
Importer of Record: {audit.importer_of_record}
[Subject to Review by Licensed Customs Broker or Legal Counsel]

SUBJECT: Prior Disclosure of Inadvertent Valuation Understatement Pertaining to Assists
         Under 19 U.S.C. § 1401a and 19 CFR § 152.103 on Entry #{audit.entry_number}

1. STATUTORY NOTICE OF VOLUNTARY DISCLOSURE
Pursuant to Section 592(c)(4) of the Tariff Act of 1930, as amended (19 U.S.C. § 1592(c)(4)),
and Section 162.74 of the Customs Regulations (19 CFR § 162.74), the Importer of Record
hereby formally discloses circumstances of a violation of 19 U.S.C. § 1592 prior to, or without
knowledge of, the formal commencement of an investigation by U.S. Customs and Border Protection.

2. AFFECTED MERCHANDISE AND ENTRY IDENTIFICATION
- Entry Number: {audit.entry_number}
- Declared Transaction Value: ${audit.declared_transaction_value:,.2f} USD
- Port of Entry: {port_of_entry}
- Applicable HTS General Duty Rate: {audit.duty_rate_ad_valorem * 100:.2f}%

3. NARRATIVE EXPLANATION OF CIRCUMSTANCES
During an internal compliance review, the Importer identified that certain assists provided to the foreign manufacturer
(specifically tools, dies, molds, and foreign engineering design qualifying under 19 U.S.C. § 1401a(h)(1)(A))
were omitted from the dutiable value declared upon entry.
[IMPORTER / COUNSEL TO VERIFY CIRCUMSTANCES OF OMISSION].

Furthermore, commercial invoice review indicates that CIF ocean freight of ${audit.international_freight_in_invoice:,.2f}
and marine insurance of ${audit.marine_insurance_in_invoice:,.2f} were included in the entered
value contrary to 19 CFR § 152.103.

4. STATUTORY RECONCILIATION & MATHEMATICAL DETERMINATION (100% PYTHON DECIMAL)
- Declared Transaction Value:               ${audit.declared_transaction_value:,.2f}
- Less: Excludable Ocean Freight/Insurance: -${audit.improper_cif_overvaluation:,.2f}
- Plus: Unapportioned Statutory Assists:    +${audit.assists_omitted_cost:,.2f}
-------------------------------------------------------------------------
- Adjusted Lawful Dutiable Value:           ${audit.adjusted_lawful_dutiable_value:,.2f}
- Lawful Customs Duty Due:                  ${audit.lawful_duty_due:,.2f}
- Customs Duty Previously Tendered:         ${audit.declared_duty_paid:,.2f}
-------------------------------------------------------------------------
- ACTUAL DUTY LOSS / UNDERPAYMENT:          ${audit.duty_underpayment:,.2f}
- STATUTORY INTEREST DUE (19 U.S.C. § 1505): ${audit.statutory_interest_19usc1505:,.2f}
=========================================================================
- TOTAL TENDER CHECK ENCLOSED (STATUTORY TENDER COMPUTED): ${audit.prior_disclosure_tender_amount:,.2f}

5. PENALTY MITIGATION EFFECTUATION
Under 19 U.S.C. § 1592(c)(4) and 19 CFR § 162.74, upon tender of the actual duty loss
plus statutory interest and satisfaction of all filing criteria, civil penalties under
19 U.S.C. § 1592(c)(4)(B) for negligence or gross negligence are limited to interest
on the loss of duty. Against the negligence maximum of ${audit.negligence_penalty_exposure:,.2f}
that is a reduction of ${audit.total_liability_avoided:,.2f} (gross negligence maximum:
${audit.gross_negligence_penalty_exposure:,.2f}). Culpability is a determination for counsel.

Respectfully submitted,
{audit.importer_of_record}
[Signature by Authorized Officer of Importer of Record or Attorney-in-Fact]

*** DRAFT -- PREPARED FOR REVIEW BY LICENSED CUSTOMS BROKER OR LEGAL COUNSEL ***
"""

        return PriorDisclosurePackage(
            filing_reference_id=ref_id,
            port_of_entry=port_of_entry,
            addressed_to=f"Port Director & FP&F Officer, Port of {port_of_entry}",
            statutory_statutes_cited=[
                "19 U.S.C. § 1401a (Value of Merchandise)",
                "19 CFR § 152.103 (Transaction Value)",
                "19 U.S.C. § 1592(c)(4) (Prior Disclosure Mitigation)",
                "19 CFR § 162.74 (Prior Disclosure Procedures)",
                "19 U.S.C. § 1505 (Statutory Interest)",
            ],
            narrative_explanation="Voluntary prior disclosure of omitted tooling and engineering assists on entry summary.",
            affected_entries=[audit.entry_number],
            actual_duty_loss=audit.duty_underpayment,
            interest_tender_amount=audit.statutory_interest_19usc1505,
            total_tender_check=audit.prior_disclosure_tender_amount,
            letter_text=letter_text,
        )
