import logging
import os
from typing import Any, Dict, List

from app.models.schemas import BoundingBox

logger = logging.getLogger(__name__)


class DocumentLayoutExtractor:
    """
    Local layout and bounding-box extractor.
    - Uses local docling parser if available.
    - Provides deterministic local fallback parser using pypdf geometry when docling is not installed.
    - Normalizes all coordinates into the [0, 1000) integer/float space.
    """
    def __init__(self):
        self._docling_available = False
        try:
            import docling  # type: ignore # noqa: F401
            self._docling_available = True
        except ImportError:
            self._docling_available = False

    @property
    def has_docling(self) -> bool:
        return bool(self._docling_available)

    def extract_bounding_boxes(self, pdf_path: str) -> List[Dict[str, Any]]:
        """
        Extracts layout regions from PDF and returns normalized [0, 1000) bounding boxes.
        """
        if not os.path.exists(pdf_path):
            return []

        # If docling is installed, invoke docling DocumentConverter
        if self._docling_available:
            try:
                from docling.document_converter import DocumentConverter  # type: ignore
                converter = DocumentConverter()
                result = converter.convert(pdf_path)
                boxes = []
                for item in result.document.iterate_items():
                    if hasattr(item, "prov") and item.prov:
                        for prov in item.prov:
                            if hasattr(prov, "bbox") and prov.bbox:
                                b = prov.bbox
                                # docling bounding box normalized to [0, 1000)
                                x_val = max(0.0, min(1000.0, float(b.l)))
                                y_val = max(0.0, min(1000.0, float(b.t)))
                                w_val = max(0.0, min(1000.0 - x_val, float(b.r - b.l)))
                                h_val = max(0.0, min(1000.0 - y_val, float(b.b - b.t)))
                                boxes.append({
                                    "text": getattr(item, "text", ""),
                                    "bounding_box": BoundingBox(
                                        x=x_val,
                                        y=y_val,
                                        width=w_val,
                                        height=h_val,
                                        page_number=int(getattr(prov, "page_no", 1)),
                                        confidence=0.95
                                    )
                                })
                if boxes:
                    return boxes
            except Exception as e:
                logger.warning("Docling extraction failed, falling back to pypdf: %s", e)

        # Deterministic local parser via pypdf text positions
        return extract_pypdf_boxes(pdf_path)

    async def extract_bounding_boxes_async(self, pdf_path: str) -> List[Dict[str, Any]]:
        """
        Non-blocking async wrapper around synchronous layout extraction
        (docling DocumentConverter or pypdf geometry), running in asyncio thread pool.
        """
        import asyncio
        return await asyncio.to_thread(self.extract_bounding_boxes, pdf_path)

def _to_display_space(
    x: float, y: float, width: float, height: float, rotation: int
) -> tuple[float, float, float, float]:
    """
    Map a point in unrotated user space (origin at the MediaBox lower-left) to display
    space with a top-left origin, honouring the page /Rotate (clockwise) value.
    Returns (X, Y_from_top, display_width, display_height).
    """
    r = rotation % 360
    if r == 90:
        return y, x, height, width
    if r == 180:
        return width - x, y, width, height
    if r == 270:
        return height - y, width - x, height, width
    return x, height - y, width, height


def extract_pypdf_boxes(pdf_path: str) -> List[Dict[str, Any]]:
    """
    Word-run bounding boxes in normalised [0, 1000) display space, page by page.

    Uses the full text rendering matrix (Tm x CTM), subtracts the MediaBox origin and
    applies /Rotate, so boxes line up with what a viewer renders. Pages with no text
    layer (scans) contribute no boxes: nothing is invented for them.
    """
    import pypdf

    boxes: List[Dict[str, Any]] = []
    try:
        reader = pypdf.PdfReader(pdf_path)
        for page_idx, page in enumerate(reader.pages):
            mb = page.mediabox
            ox, oy = float(mb.left), float(mb.bottom)
            pw, ph = float(mb.width), float(mb.height)
            rotation = int(page.get("/Rotate", 0) or 0)

            def _visitor(text, cm, tm, font_dict, font_size, _ox=ox, _oy=oy, _pw=pw, _ph=ph, _rot=rotation, _page=page_idx + 1):
                stripped = text.strip()
                if not stripped:
                    return
                m = pypdf.mult(tm, cm)
                scale = (m[0] ** 2 + m[1] ** 2) ** 0.5 or 1.0
                f_size = float(font_size or 10.0) * scale
                bx, by = float(m[4]) - _ox, float(m[5]) - _oy
                X, Y, dw, dh = _to_display_space(bx, by, _pw, _ph, _rot)
                x_val = max(0.0, min(990.0, X / dw * 1000.0))
                y_val = max(0.0, min(990.0, (Y - f_size) / dh * 1000.0))
                w_val = max(5.0, len(stripped) * f_size * 0.55 / dw * 1000.0)
                h_val = max(5.0, f_size * 1.25 / dh * 1000.0)
                rx, ry = round(x_val, 1), round(y_val, 1)
                rw = round(min(1000.0 - rx, w_val), 1)
                rh = round(min(1000.0 - ry, h_val), 1)
                boxes.append({
                    "text": stripped,
                    "bounding_box": BoundingBox(x=rx, y=ry, width=rw, height=rh, page_number=_page, confidence=0.95),
                })

            page.extract_text(visitor_text=_visitor)
    except Exception as e:
        logger.error("pypdf layout extraction failed for %s: %s", pdf_path, e)
    return boxes


layout_extractor = DocumentLayoutExtractor()
