"""
PyMuPDF Vector PDF Certificate Engine
Renders dynamic fields onto vector PDF templates using structural text search,
relative bounding boxes, dynamic area clearing/redaction, and crisp vector font injection.
Supports both vector PDF export and high-resolution raster PNG export.
"""

import dataclasses
import io
import re
from typing import Dict, Any, List, Tuple
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


def _is_explicit_solid_fill(clear_bg_color: Any) -> bool:
    """Returns True only when clear_bg_color specifies an explicit non-transparent/non-auto fill."""
    if not clear_bg_color:
        return False
    normalized = str(clear_bg_color).strip().lower()
    return normalized not in ("", "none", "transparent", "false", "auto")


def _wrap_text_pdf(text: str, fontname: str, fontsize: float, max_width: float) -> List[str]:
    """Wraps text into lines that fit within max_width using PyMuPDF text length measurement."""
    lines: List[str] = []
    for paragraph in text.splitlines() or [""]:
        words = paragraph.split()
        if not words:
            lines.append("")
            continue
        current = words[0]
        for word in words[1:]:
            candidate = f"{current} {word}"
            if fitz.get_text_length(candidate, fontname=fontname, fontsize=fontsize) <= max_width:
                current = candidate
            else:
                lines.append(current)
                current = word
        lines.append(current)
    return lines


def _ellipsize_lines_pdf(
    lines: List[str],
    max_lines: int,
    fontname: str,
    fontsize: float,
    max_width: float,
) -> List[str]:
    """Truncates lines to max_lines and appends '...' to the final line so it fits max_width."""
    kept = list(lines[: max(1, max_lines)])
    last = kept[-1]
    if len(lines) > max_lines and not last.endswith("..."):
        last = f"{last}..."
    while len(last) > 3 and fitz.get_text_length(last, fontname=fontname, fontsize=fontsize) > max_width:
        base = last[:-4] if last.endswith("...") else last[:-1]
        last = f"{base.rstrip()}..."
    if fitz.get_text_length(last, fontname=fontname, fontsize=fontsize) > max_width:
        last = "..."
    kept[-1] = last
    return kept


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

        # 1. Defensively clear configured wipe areas only for explicit non-transparent/non-auto fills
        has_redactions = False
        for field_name, config in manifest.fields.items():
            fill_color = getattr(config, "clear_bg_color", None)
            if config.clear_area and _is_explicit_solid_fill(fill_color):
                x1, y1, x2, y2 = config.clear_area
                clear_r = fitz.Rect(page_w * x1, page_h * y1, page_w * x2, page_h * y2)
                bg_color = _parse_hex_color(str(fill_color))
                page.add_redact_annot(clear_r, fill=bg_color)
                has_redactions = True

        # 2. Defensively redact any curly-brace placeholder tags like {{name}}, {{work}}, {{date}}
        page_text = page.get_text()
        found_tags = set(re.findall(r"\{\{([^}]+)\}\}", page_text))
        for tag in found_tags:
            tag_str = f"{{{{{tag}}}}}"
            occurrences = page.search_for(tag_str)
            for occ in occurrences:
                # Expand slightly to erase full character boundaries without painting an opaque box
                r_exp = fitz.Rect(occ.x0 - 2, occ.y0 - 2, occ.x1 + 2, occ.y1 + 2)
                page.add_redact_annot(r_exp, fill=None)
                has_redactions = True

        if has_redactions:
            page.apply_redactions()

        overflowed = False
        warnings: List[str] = []

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

            max_h_pct = getattr(config, "max_h_pct", None)
            max_lines = max(1, int(getattr(config, "max_lines", 3) or 3))
            v_align = str(getattr(config, "v_align", "center") or "center").lower()
            overflow_policy = str(getattr(config, "overflow_policy", "shrink_wrap") or "shrink_wrap").lower()
            line_spacing = float(getattr(config, "line_spacing", 1.3) or 1.3)

            # Determine horizontal bounding box
            anchor_y = page_h * config.y_pct
            anchor_x0 = None
            if config.anchor_phrase:
                instances = page.search_for(config.anchor_phrase)
                if instances:
                    anchor_r = instances[0]
                    box_w = page_w * config.max_w_pct
                    anchor_x0 = (page_w - box_w) / 2
                    anchor_y = anchor_r.y1 + 10 + (page_h * config.font_size_pct * 0.9)

            if anchor_x0 is None:
                box_w = page_w * config.max_w_pct
                if config.clear_area:
                    clear_w = page_w * (config.clear_area[2] - config.clear_area[0])
                    inset = max(2, clear_w * 0.04)
                    effective_clear_w = clear_w - (inset * 2)
                    box_w = max(box_w, effective_clear_w)

                if config.align == "center":
                    x0 = (page_w * config.x_pct) - (box_w / 2)
                elif config.align == "right":
                    x0 = (page_w * config.x_pct) - box_w
                else:
                    x0 = page_w * config.x_pct
            else:
                x0 = anchor_x0

            # Font selection
            fam = (config.font_family or "").lower()
            if "serif" in fam:
                font_choice = "tiro"
            elif "script" in fam:
                font_choice = "tiit"
            else:
                font_choice = "helv"

            align_val = 1 if config.align == "center" else (2 if config.align == "right" else 0)
            color_tuple = _parse_hex_color(config.color)

            # Font size calculation in PDF points (72 DPI)
            font_size = max(11, int(page_h * config.font_size_pct * 0.78))
            min_size = max(9, int(page_h * (getattr(config, "min_font_size_pct", None) or 0.012) * 0.78))

            # Maximum allowed box height
            if max_h_pct is not None:
                max_box_h = page_h * float(max_h_pct)
            elif config.clear_area:
                max_box_h = max(
                    page_h * (config.clear_area[3] - config.clear_area[1]),
                    font_size * line_spacing * max_lines,
                )
            else:
                max_box_h = max(page_h * config.font_size_pct * 1.8, font_size * line_spacing * max_lines)

            # Auto-downscale until wrapped lines fit box_w, max_lines, and max_box_h
            fitted = False
            lines: List[str] = [text_str]
            while font_size >= min_size:
                lines = _wrap_text_pdf(text_str, font_choice, font_size, box_w)
                block_h = len(lines) * (font_size * line_spacing)
                widths_ok = all(
                    fitz.get_text_length(line, fontname=font_choice, fontsize=font_size) <= box_w
                    for line in lines
                )
                height_ok = (max_h_pct is None) or (block_h <= max_box_h)
                if widths_ok and len(lines) <= max_lines and height_ok:
                    fitted = True
                    break
                if font_size == min_size:
                    break
                font_size -= 1

            if not fitted:
                overflowed = True
                warnings.append(
                    f"Field '{field_name}' overflowed bounding box at minimum font size ({min_size}pt)."
                )
                if overflow_policy == "ellipsize":
                    allowed_lines = max_lines
                    if max_h_pct is not None:
                        allowed_by_h = max(1, int(max_box_h // (font_size * line_spacing)))
                        allowed_lines = min(allowed_lines, allowed_by_h)
                    lines = _ellipsize_lines_pdf(lines, allowed_lines, font_choice, font_size, box_w)

            render_text = "\n".join(lines)
            block_h = len(lines) * (font_size * line_spacing)

            # Vertical alignment relative to region around anchor_y
            if v_align == "top":
                y0 = anchor_y - (max_box_h / 2)
            elif v_align == "bottom":
                y0 = (anchor_y + (max_box_h / 2)) - block_h
            else:
                y0 = anchor_y - (block_h / 2)

            # Add slight vertical padding so PyMuPDF insert_textbox doesn't reject descenders
            target_rect = fitz.Rect(x0, y0, x0 + box_w, y0 + block_h + (font_size * 0.5))
            rc = page.insert_textbox(
                target_rect,
                render_text,
                fontsize=font_size,
                fontname=font_choice,
                color=color_tuple,
                align=align_val,
            )
            if rc < 0:
                # Retry with expanded vertical rect if PyMuPDF line height exceeded estimate
                expanded_rect = fitz.Rect(x0, y0, x0 + box_w, y0 + block_h + (font_size * 1.5))
                rc_retry = page.insert_textbox(
                    expanded_rect,
                    render_text,
                    fontsize=font_size,
                    fontname=font_choice,
                    color=color_tuple,
                    align=align_val,
                )
                if rc_retry < 0 and not overflowed:
                    overflowed = True
                    warnings.append(
                        f"Field '{field_name}' could not fit cleanly inside PDF textbox at {font_size}pt."
                    )

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

        render_field_names = {f.name for f in dataclasses.fields(RenderResult)}
        result_kwargs: Dict[str, Any] = {
            "content": content,
            "filename": filename,
            "mime_type": mime_type,
            "metadata": {
                "format": out_fmt,
                "pages": 1,
                "overflowed": overflowed,
                "warnings": warnings,
            },
        }
        if "overflowed" in render_field_names:
            result_kwargs["overflowed"] = overflowed
        if "warnings" in render_field_names:
            result_kwargs["warnings"] = warnings
        return RenderResult(**result_kwargs)
