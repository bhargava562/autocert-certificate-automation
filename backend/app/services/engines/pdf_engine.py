"""
PyMuPDF Vector PDF Certificate Engine
Renders dynamic fields onto vector PDF templates using structural text search,
relative bounding boxes, dynamic area clearing/redaction, and crisp vector font injection.
Supports both vector PDF export and high-resolution raster PNG export.
"""

import io
import re
from typing import Dict, Any, Tuple
import pymupdf as fitz
from ..protocols import CertificateEngine
from ..models import TemplateManifest, RenderResult


def _parse_hex_color(color_str: str) -> Tuple[float, float, float]:
    """Converts a hex color code like '#1A5C47' to an RGB float tuple (0.0 - 1.0)."""
    c = color_str.lstrip("#")
    if len(c) == 6:
        try:
            return (
                int(c[0:2], 16) / 255.0,
                int(c[2:4], 16) / 255.0,
                int(c[4:6], 16) / 255.0,
            )
        except ValueError:
            pass
    return (0.1, 0.1, 0.1)


class PyMuPdfEngine:
    """Renders certificates directly from vector PDF templates."""

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
        if doc.page_count == 0:
            raise ValueError("PDF template contains no pages.")

        page = doc[0]
        rect = page.rect
        page_w, page_h = rect.width, rect.height

        # 1. Defensively clear configured wipe areas from the manifest
        for field_name, config in manifest.fields.items():
            if config.clear_area:
                x1, y1, x2, y2 = config.clear_area
                clear_r = fitz.Rect(page_w * x1, page_h * y1, page_w * x2, page_h * y2)
                bg_color = _parse_hex_color(config.clear_bg_color or "#FFFFFF")
                page.add_redact_annot(clear_r, fill=bg_color)

        # 2. Defensively redact any curly-brace placeholder tags like {{name}}, {{work}}, {{date}}
        page_text = page.get_text()
        found_tags = set(re.findall(r"\{\{([^}]+)\}\}", page_text))
        for tag in found_tags:
            tag_str = f"{{{{{tag}}}}}"
            occurrences = page.search_for(tag_str)
            for occ in occurrences:
                # Expand slightly to erase full character boundaries
                r_exp = fitz.Rect(occ.x0 - 2, occ.y0 - 2, occ.x1 + 2, occ.y1 + 2)
                # Use manifest field bg color if available, else #F9F9F9
                page.add_redact_annot(r_exp, fill=(249 / 255.0, 249 / 255.0, 249 / 255.0))

        page.apply_redactions()

        # 3. Render fields
        for field_name, config in manifest.fields.items():
            val = fields.get(field_name)
            if val is None:
                if field_name in ("recipient_name", "name", "full_name"):
                    val = fields.get("full_name") or fields.get("recipient_name") or fields.get("name")
                elif field_name in ("achievement_text", "description"):
                    val = fields.get("achievement_text") or fields.get("description")
                elif field_name in ("issue_date", "date"):
                    val = fields.get("issue_date") or fields.get("date")

            if val is None:
                continue

            text_str = str(val).strip()
            if not text_str:
                continue

            target_rect = None

            # Anchor phrase lookup
            if config.anchor_phrase:
                instances = page.search_for(config.anchor_phrase)
                if instances:
                    anchor_r = instances[0]
                    target_w = page_w * config.max_w_pct
                    x0 = (page_w - target_w) / 2
                    y0 = anchor_r.y1 + 10
                    y1 = y0 + (page_h * config.font_size_pct * 1.8)
                    target_rect = fitz.Rect(x0, y0, x0 + target_w, y1)

            # Proportional bounding box calculation
            if target_rect is None:
                box_w = page_w * config.max_w_pct
                # Give multiline text larger bounding box
                is_multiline = "\n" in text_str or len(text_str) > 60
                height_factor = 2.4 if is_multiline else 1.6
                box_h = page_h * (config.font_size_pct * height_factor)

                if config.align == "center":
                    x0 = (page_w - box_w) / 2
                elif config.align == "right":
                    x0 = (page_w * config.x_pct) - box_w
                else:
                    x0 = page_w * config.x_pct

                y0 = (page_h * config.y_pct) - (box_h / 2)
                target_rect = fitz.Rect(x0, y0, x0 + box_w, y0 + box_h)

            # Font size calculation in PDF points (72 DPI)
            font_size = max(11, int(page_h * config.font_size_pct * 0.78))

            # Alignment: 0=Left, 1=Center, 2=Right
            align_val = 1 if config.align == "center" else (2 if config.align == "right" else 0)

            # Color tuple
            color_tuple = _parse_hex_color(config.color)

            # Font selection
            fam = (config.font_family or "").lower()
            if "serif" in fam:
                font_choice = "tiro"
            elif "script" in fam:
                font_choice = "tiit"
            else:
                font_choice = "helv"

            # Auto-downscale until text fits cleanly inside target bounding box
            min_size = max(9, int(page_h * (config.min_font_size_pct or 0.012) * 0.78))
            while font_size >= min_size:
                rc = page.insert_textbox(
                    target_rect,
                    text_str,
                    fontsize=font_size,
                    fontname=font_choice,
                    color=color_tuple,
                    align=align_val
                )
                if rc >= 0:
                    break
                font_size -= 1

        cert_id = fields.get("certificate_id", "cert")
        safe_name = (fields.get("full_name") or fields.get("recipient_name") or "recipient").replace(" ", "_")

        out_fmt = (manifest.default_format or "pdf").lower()
        if out_fmt == "png":
            # Rasterize high-resolution PNG (200 DPI for crisp readability)
            pix = page.get_pixmap(dpi=200)
            content = pix.tobytes("png")
            filename = f"{cert_id}_{safe_name}.png"
            mime_type = "image/png"
        else:
            # Vector PDF export
            out_buf = io.BytesIO()
            doc.save(out_buf)
            content = out_buf.getvalue()
            filename = f"{cert_id}_{safe_name}.pdf"
            mime_type = "application/pdf"

        doc.close()

        return RenderResult(
            content=content,
            filename=filename,
            mime_type=mime_type,
            metadata={"format": out_fmt, "pages": 1}
        )
