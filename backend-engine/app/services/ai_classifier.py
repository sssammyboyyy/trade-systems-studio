import logging
from typing import List, Optional, TypeVar

from pydantic import BaseModel, Field

from app.core.config import settings

logger = logging.getLogger(__name__)

T = TypeVar("T", bound=BaseModel)

class DocumentRoute(BaseModel):
    document_type: str = Field(description="Detected document type: commercial_invoice, freight_bill, or entry_summary")
    concept_id: str = Field(description="Routed concept: concept_1_customs, concept_2_freight, or concept_3_drawback")
    confidence: float = Field(ge=0.0, le=1.0, description="Routing confidence score")
    summary: str = Field(description="Summary of document purpose and primary parties")

class GRIReasoningResult(BaseModel):
    declared_hts: str = Field(description="Declared HTS subheading")
    lawful_hts: str = Field(description="Lawful HTS subheading determined under GRI 1-6")
    gri_rules_applied: List[str] = Field(description="GRI rules applied, e.g. ['GRI 1', 'GRI 6']")
    classification_rationale: str = Field(description="Legal reasoning under WCO GRI rules")
    section_301_applicable: bool = Field(description="Whether Section 301 China tariffs apply")
    confidence: float = Field(ge=0.0, le=1.0, description="Classification confidence")

class TradeAIClassifier:
    """
    AI Classification & Routing using google-genai + instructor Python SDK:
    - the classifier model (GEMINI_CLASSIFIER_MODEL, default gemini-2.5-flash) for complex GRI 1-6 reasoning, HS code cross-validation, and legal discrepancy justification.
    - the router model (GEMINI_ROUTER_MODEL, default gemini-2.5-flash-lite) for high-throughput field extraction and document routing.
    - Strict mathematical determinism: Never uses LLM for arithmetic or currency calculations.
    - Gracefully degrades to local deterministic fallback when no API key is present or on API failure.
    """
    def __init__(self):
        self.api_key = settings.GEMINI_API_KEY.strip() if settings.GEMINI_API_KEY else ""
        self.router_model = settings.GEMINI_ROUTER_MODEL
        self.classifier_model = settings.GEMINI_CLASSIFIER_MODEL
        self.client = None
        self.instructor_client = None
        if self.api_key:
            try:
                from google import genai
                self.client = genai.Client(api_key=self.api_key)
                try:
                    import instructor
                    self.instructor_client = instructor.from_genai(self.client)
                except Exception as exc:
                    logger.warning("Instructor GenAI wrapper unavailable, using native google-genai client: %s", exc)
                    self.instructor_client = None
            except Exception as exc:
                logger.warning("Failed to initialize google-genai client; falling back to deterministic local mode: %s", exc)
                self.client = None
                self.instructor_client = None

    @property
    def is_online(self) -> bool:
        return self.client is not None

    def route_document(self, text_content: str) -> Optional[DocumentRoute]:
        """
        Routes document using configured GEMINI_ROUTER_MODEL with Structured Outputs.
        Supports instructor or native google-genai structured generation.
        """
        if not self.client:
            return None
        try:
            # Check instructor integration first if available
            if self.instructor_client is not None:
                try:
                    routed_doc: DocumentRoute = self.instructor_client.chat.completions.create(
                        model=self.router_model,
                        response_model=DocumentRoute,
                        messages=[
                            {
                                "role": "user",
                                "content": (
                                    "You are a trade document router. Analyze the following document text and route "
                                    "it to the matching compliance workflow:\n\n" + text_content
                                ),
                            }
                        ],
                        temperature=0.0,
                    )
                    return routed_doc
                except Exception as e:
                    logger.warning("Instructor routing failed, falling back to native client: %s", e)

            from google.genai import types
            response = self.client.models.generate_content(
                model=self.router_model,
                contents=(
                    "You are a trade document router. Analyze the following document text and route "
                    "it to the matching compliance workflow:\n\n" + text_content
                ),
                config=types.GenerateContentConfig(
                    response_mime_type="application/json",
                    response_schema=DocumentRoute,
                    temperature=0.0,
                ),
            )
            if response.text:
                return DocumentRoute.model_validate_json(response.text)
        except Exception as e:
            logger.error("GenAI document routing failed: %s", e)
            return None
        return None

    def analyze_gri_classification(
        self,
        item_description: str,
        declared_hts: str
    ) -> Optional[GRIReasoningResult]:
        """
        Evaluates WCO General Rules of Interpretation (GRI 1-6) using configured GEMINI_CLASSIFIER_MODEL.
        """
        if not self.client:
            return None
        try:
            if self.instructor_client is not None:
                try:
                    gri_result: GRIReasoningResult = self.instructor_client.chat.completions.create(
                        model=self.classifier_model,
                        response_model=GRIReasoningResult,
                        messages=[
                            {
                                "role": "user",
                                "content": (
                                    f"Perform a strict WCO GRI 1-6 customs classification review for item: "
                                    f"'{item_description}', which was declared under HTS '{declared_hts}'. "
                                    f"Identify lawful classification and legal rationale under GRI hierarchical rules."
                                ),
                            }
                        ],
                        temperature=0.0,
                    )
                    return gri_result
                except Exception as e:
                    logger.warning("Instructor GRI analysis failed, falling back to native client: %s", e)

            from google.genai import types
            response = self.client.models.generate_content(
                model=self.classifier_model,
                contents=(
                    f"Perform a strict WCO GRI 1-6 customs classification review for item: "
                    f"'{item_description}', which was declared under HTS '{declared_hts}'. "
                    f"Identify lawful classification and legal rationale under GRI hierarchical rules."
                ),
                config=types.GenerateContentConfig(
                    response_mime_type="application/json",
                    response_schema=GRIReasoningResult,
                    temperature=0.0,
                ),
            )
            if response.text:
                return GRIReasoningResult.model_validate_json(response.text)
        except Exception as e:
            logger.error("GenAI GRI classification analysis failed: %s", e)
            return None
        return None

ai_classifier = TradeAIClassifier()
