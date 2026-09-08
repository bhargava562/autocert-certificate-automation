"""
PyMuPDF Vector PDF Certificate Engine
Renders dynamic fields onto vector PDF templates using structural text search,
relative bounding boxes, and crisp vector font injection.
"""

import io
from typing import Dict, Any
import pymupdf as fitz
from ..protocols import CertificateEngine
from ..models import TemplateManifest, RenderResult

class PyMuPdfEngine:
    """Renders certificates directly from vector PDF templates"""

    def can_handle(self, filename_or_ext: str) -> bool:
        ext = filename_or_ext.lower().split(".")[-1]
        return ext == "pdf"

    def render(
        self,
        template_bytes: bytes,
        fields: Dict[str, Any],
        manifest: TemplateManifest
    ) -> RenderResult:
        doc = fitz.open(stream=template_bytes, filetype="pdf")
        page = doc[0]
        rect = page.rect
        page_w, page_h = rect.width, rect.height

        for field_name, config in manifest.fields.items():
            val = fields.get(field_name)
            if val is None:
                continue
            text_str = str(val).strip()
            if not text_str:
                continue

            target_rect = None

            # 1. Check if anchor phrase or placeholder exists in the document
            if config.anchor_phrase:
                instances = page.search_for(config.anchor_phrase)
                if instances:
                    anchor_r = instances[0]
                    # Target rectangle directly below anchor
                    target_w = page_w * config.max_w_pct
                    x0 = (page_w - target_w) / 2
                    y0 = anchor_r.y1 + 10
                    y1 = y0 + (page_h * config.font_size_pct * 1.8)
                    target_rect = fitz.Rect(x0, y0, x0 + target_w, y1)

            # Check for placeholder like {{name}}
            placeholder_tag = f"{{{{{field_name}}}}}"
            placeholder_instances = page.search_for(placeholder_tag)
            if placeholder_instances:
                target_rect = placeholder_instances[0]
                # Redact the placeholder text
                page.add_redaction_annot(target_rect, fill=(1, 1, 1))
                page.apply_redactions()

            # 2. Fallback to relative percentages
            if target_rect is None:
                box_w = page_w * config.max_w_pct
                box_h = page_h * (config.font_size_pct * 1.6)
                if config.align == "center":
                    x0 = (page_w - box_w) / 2
                else:
                    x0 = page_w * config.x_pct
                y0 = page_h * config.y_pct - (box_h / 2)
                target_rect = fitz.Rect(x0, y0, x0 + box_w, y0 + box_h)

            # Calculate font size in PDF points (72 DPI)
            font_size = max(14, int(page_h * config.font_size_pct * 0.75))

            # Alignment: 0=Left, 1=Center, 2=Right
            align_val = 1 if config.align == "center" else (2 if config.align == "right" else 0)

            # Parse hex color to RGB tuple (0.0 to 1.0)
            c = config.color.lstrip("#")
            if len(c) == 6:
                r = int(c[0:2], 16) / 255.0
                g = int(c[2:4], 16) / 255.0
                b = int(c[4:6], 16) / 255.0
                color_tuple = (r, g, b)
            else:
                color_tuple = (0.2, 0.2, 0.2)

            font_choice = "tiro" if "serif" in config.font_family else "helv"

            # Insert text with auto-fitting into bounding box
            # If text overflows, reduce font size
            while font_size > 10:
                rc = page.insert_textbox(
                    target_rect,
                    text_str,
                    fontsize=font_size,
                    fontname=font_choice,
                    color=color_tuple,
                    align=align_val
                )
                if rc >= 0:  # rc >= 0 means text fit successfully
                    break
                font_size -= 2

        out_buf = io.BytesIO()
        doc.save(out_buf)
        doc.close()

        cert_id = fields.get("certificate_id", "cert")
        safe_name = fields.get("recipient_name", "recipient").replace(" ", "_")
        filename = f"{cert_id}_{safe_name}.pdf"

        return RenderResult(
            content=out_buf.getvalue(),
            filename=filename,
            mime_type="application/pdf",
            metadata={"format": "pdf", "pages": 1}
        )
