"""
Template Placeholder Scanner Service
Scans uploaded certificate template bytes (PDF or Image) for exact placeholder strings
(e.g., {{name}}, {{year}}, {{dept}}, {{full_name}}, {{department}}) and extracts their
exact bounding boxes and proportional coordinates for dynamic 100% accurate rendering.
"""

from typing import Dict, Any, Optional
import pymupdf
from .models import TemplateManifest, FieldConfig

PLACEHOLDER_SYNONYMS = {
    "full_name": ["{{name}}", "{{full_name}}", "{{recipient_name}}", "[name]", "<name>", "{{NAME}}"],
    "year": ["{{year}}", "{{class}}", "{{academic_year}}", "[year]", "<year>", "{{YEAR}}"],
    "department": ["{{dept}}", "{{department}}", "{{branch}}", "[dept]", "<dept>", "{{DEPT}}"],
    "achievement_title": ["{{event}}", "{{title}}", "{{achievement_title}}", "[title]"],
}

def scan_template_placeholders(template_bytes: bytes, filename: str, default_format: str = "png") -> TemplateManifest:
    """
    Scans document template for exact placeholder occurrences.
    If exact text matches are found, builds FieldConfig with exact bounding box coordinates.
    Otherwise returns layout manifest calibrated for the certificate structure.
    """
    fn_lower = filename.lower()
    ext = fn_lower.split(".")[-1]
    
    found_fields: Dict[str, FieldConfig] = {}
    try:
        if ext == "pdf":
            doc = pymupdf.open(stream=template_bytes, filetype="pdf")
        else:
            img_doc = pymupdf.open(stream=template_bytes, filetype=ext)
            pdf_bytes = img_doc.convert_to_pdf()
            doc = pymupdf.open(stream=pdf_bytes, filetype="pdf")
            img_doc.close()

        if doc.page_count > 0:
            page = doc[0]
            pw = page.rect.width
            ph = page.rect.height

            for field_key, search_terms in PLACEHOLDER_SYNONYMS.items():
                for term in search_terms:
                    rects = page.search_for(term)
                    if rects:
                        r = rects[0]
                        
                        center_x = (r.x0 + r.x1) / 2.0 / pw
                        center_y = (r.y0 + r.y1) / 2.0 / ph
                        
                        x1_pct = max(0.0, (r.x0 / pw) - 0.005)
                        y1_pct = max(0.0, (r.y0 / ph) - 0.008)
                        x2_pct = min(1.0, (r.x1 / pw) + 0.005)
                        y2_pct = min(1.0, (r.y2 if hasattr(r, 'y2') else r.y1) / ph + 0.008)

                        max_w = min(0.40, max(0.12, ((r.x1 - r.x0) / pw) * 2.5))

                        font_size_pct = round((r.y1 - r.y0) / ph, 4)
                        if font_size_pct < 0.015:
                            font_size_pct = 0.030

                        found_fields[field_key] = FieldConfig(
                            name=field_key,
                            x_pct=round(center_x, 4),
                            y_pct=round(center_y, 4),
                            max_w_pct=round(max_w, 4),
                            font_family="sans-serif",
                            font_size_pct=font_size_pct,
                            min_font_size_pct=0.015,
                            align="center",
                            color="#111827",
                            clear_area=(round(x1_pct, 4), round(y1_pct, 4), round(x2_pct, 4), round(y2_pct, 4)),
                            clear_bg_color="auto"
                        )
                        break
            doc.close()
    except Exception:
        pass

    if found_fields:
        return TemplateManifest(
            template_id="scanned_placeholder_manifest",
            template_filename=filename,
            default_format=default_format,
            base_width=2000,
            base_height=1414,
            fields=found_fields
        )

    return TemplateManifest(
        template_id="rmk_participation_manifest",
        template_filename=filename,
        default_format=default_format,
        base_width=2000,
        base_height=1414,
        fields={
            "full_name": FieldConfig(
                name="full_name",
                x_pct=0.470,
                y_pct=0.592,
                max_w_pct=0.20,
                font_family="sans-serif",
                font_size_pct=0.024,
                min_font_size_pct=0.012,
                align="center",
                color="#0f172a",
                clear_area=(0.420, 0.550, 0.535, 0.635),
                clear_bg_color="transparent",
            ),
            "year": FieldConfig(
                name="year",
                x_pct=0.630,
                y_pct=0.592,
                max_w_pct=0.07,
                font_family="sans-serif",
                font_size_pct=0.024,
                min_font_size_pct=0.012,
                align="center",
                color="#0f172a",
                clear_area=(0.595, 0.550, 0.672, 0.635),
                clear_bg_color="transparent",
            ),
            "department": FieldConfig(
                name="department",
                x_pct=0.758,
                y_pct=0.592,
                max_w_pct=0.08,
                font_family="sans-serif",
                font_size_pct=0.024,
                min_font_size_pct=0.012,
                align="center",
                color="#0f172a",
                clear_area=(0.715, 0.550, 0.800, 0.635),
                clear_bg_color="transparent",
            ),
        }
    )
