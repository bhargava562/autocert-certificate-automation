"""
Pillow-Based Image Certificate Engine
Renders text onto flat or raster image templates with dynamic auto-scaling,
exact text centering, and multi-line wrapping.
"""

import io
from typing import Dict, Any
from PIL import Image, ImageDraw
from ..protocols import CertificateEngine
from ..models import TemplateManifest, RenderResult
from ..text_fitting import TextFittingService

class PillowImageEngine:
    """Renders certificates from image templates (PNG, JPEG, WebP)"""

    def __init__(self, text_service: TextFittingService):
        self.text_service = text_service

    def can_handle(self, filename_or_ext: str) -> bool:
        ext = filename_or_ext.lower().split(".")[-1]
        return ext in ("png", "jpg", "jpeg", "webp")

    def _compute_effective_max_width(self, canvas_w: int, config) -> int:
        """
        Derives the effective maximum pixel width for text rendering.
        When a clear_area is defined, uses it as the hard boundary to prevent
        text from bleeding into adjacent fields. Otherwise falls back to max_w_pct.
        """
        max_w_from_pct = int(canvas_w * config.max_w_pct)
        if config.clear_area:
            clear_w = int(canvas_w * (config.clear_area[2] - config.clear_area[0]))
            # Use whichever is larger to give the text room, but cap at clear_area
            # width with a small inset (4% padding on each side) for visual breathing room
            inset = max(4, int(clear_w * 0.04))
            effective_w = clear_w - (inset * 2)
            return max(effective_w, max_w_from_pct)
        return max_w_from_pct

    def render(
        self,
        template_bytes: bytes,
        fields: Dict[str, Any],
        manifest: TemplateManifest
    ) -> RenderResult:
        # Load image template
        img = Image.open(io.BytesIO(template_bytes)).convert("RGB")
        draw = ImageDraw.Draw(img)
        canvas_w, canvas_h = img.size

        # Render each field defined in the manifest
        for field_name, config in manifest.fields.items():
            # 1. Wipe clear_area first if specified and non-transparent
            if config.clear_area:
                fill_color = config.clear_bg_color
                if fill_color and str(fill_color).lower() not in ("none", "transparent", "false"):
                    if str(fill_color).lower() == "auto":
                        fill_color = "#FFFFFF"
                    x1 = int(canvas_w * config.clear_area[0])
                    y1 = int(canvas_h * config.clear_area[1])
                    x2 = int(canvas_w * config.clear_area[2])
                    y2 = int(canvas_h * config.clear_area[3])
                    draw.rectangle([(x1, y1), (x2, y2)], fill=fill_color)

            # 2. Extract value for rendering
            val = fields.get(field_name)
            if val is None:
                # Check known synonym mappings
                if field_name in ("recipient_name", "name", "full_name"):
                    val = fields.get("full_name") or fields.get("recipient_name") or fields.get("name")
                elif field_name in ("year", "academic_year", "class"):
                    val = fields.get("year") or fields.get("academic_year") or fields.get("batch_year") or fields.get("class")
                elif field_name in ("department", "dept", "branch"):
                    val = fields.get("department") or fields.get("dept") or fields.get("branch") or fields.get("stream")
                elif field_name in ("event_name", "eventname"):
                    val = fields.get("event_name") or fields.get("eventname") or fields.get("achievement_title")
                elif field_name in ("role", "achievement_title", "title"):
                    val = fields.get("role") or fields.get("achievement_title") or fields.get("title")
                elif field_name in ("date", "issue_date"):
                    val = fields.get("issue_date") or fields.get("date")

            if val is None:
                continue
            text_str = str(val).strip()
            if not text_str:
                continue

            max_width = self._compute_effective_max_width(canvas_w, config)
            target_size = max(10, int(canvas_h * config.font_size_pct))
            min_size = (
                max(8, int(canvas_h * config.min_font_size_pct))
                if getattr(config, "min_font_size_pct", None)
                else config.min_font_size
            )

            # Determine if text should be rendered in multi-line wrapping mode
            force_multiline = len(text_str) > 70 or "\n" in text_str or config.font_size_pct <= 0.020

            if not force_multiline:
                # Try single-line auto-scaled fit first
                font, actual_size, text_w = self.text_service.fit_text_to_width(
                    draw=draw,
                    text=text_str,
                    font_family=config.font_family,
                    target_size=target_size,
                    max_width=max_width,
                    min_size=min_size
                )

                # If text still overflows at min_size, fall back to multi-line wrapping
                if text_w > max_width:
                    force_multiline = True

            if force_multiline:
                # Multi-line wrapping mode: auto-scale font then wrap into lines
                # First try to fit at target_size with wrapping; if the wrapped font
                # is still too large, scale down until wrapping produces a reasonable
                # number of lines that fit within the clear_area height.
                wrap_size = target_size
                wrap_step = max(1, int(target_size * 0.05))
                max_lines_allowed = 3  # Prevent excessive line count

                if config.clear_area:
                    clear_h_px = int(canvas_h * (config.clear_area[3] - config.clear_area[1]))
                else:
                    clear_h_px = int(canvas_h * 0.15)  # Reasonable default region height

                best_font = None
                best_lines = None
                best_size = wrap_size

                while wrap_size >= min_size:
                    font = self.text_service.load_font(config.font_family, wrap_size)
                    lines = self.text_service.wrap_text(draw, text_str, font, max_width)
                    line_height = int(wrap_size * config.line_spacing)
                    total_text_h = len(lines) * line_height

                    if total_text_h <= clear_h_px and len(lines) <= max_lines_allowed:
                        best_font = font
                        best_lines = lines
                        best_size = wrap_size
                        break

                    best_font = font
                    best_lines = lines
                    best_size = wrap_size
                    wrap_size -= wrap_step

                font = best_font or self.text_service.load_font(config.font_family, min_size)
                lines = best_lines or self.text_service.wrap_text(draw, text_str, font, max_width)
                line_height = int(best_size * config.line_spacing)
                total_text_h = len(lines) * line_height

                start_y = int(canvas_h * config.y_pct) - (total_text_h // 2)
                curr_y = start_y

                for line in lines:
                    bbox = draw.textbbox((0, 0), line, font=font)
                    line_w = bbox[2] - bbox[0]
                    if config.align == "center":
                        if config.clear_area:
                            box_center_x = (config.clear_area[0] + config.clear_area[2]) / 2.0 * canvas_w
                            line_x = int(box_center_x - (line_w / 2.0))
                        else:
                            line_x = self.text_service.calculate_center_x(canvas_w, line_w)
                    elif config.align == "right":
                        line_x = int(canvas_w * config.x_pct) - line_w
                    else:
                        line_x = int(canvas_w * config.x_pct)

                    draw.text((line_x, curr_y), line, font=font, fill=config.color)
                    curr_y += line_height
            else:
                # Single-line rendering: text fits within max_width at actual_size
                if config.align == "center":
                    if config.clear_area:
                        box_center_x = (config.clear_area[0] + config.clear_area[2]) / 2.0 * canvas_w
                        x = int(box_center_x - (text_w / 2.0))
                    else:
                        x = self.text_service.calculate_center_x(canvas_w, text_w)
                elif config.align == "right":
                    x = int(canvas_w * config.x_pct) - text_w
                else:
                    x = int(canvas_w * config.x_pct)

                y = int(canvas_h * config.y_pct) - (actual_size // 2)
                draw.text((x, y), text_str, font=font, fill=config.color)

        # Export result (PNG or PDF based on manifest default_format)
        out_buf = io.BytesIO()
        out_fmt = manifest.default_format.lower()
        cert_id = fields.get("certificate_id", "cert")
        safe_name = (fields.get("full_name") or fields.get("recipient_name") or "recipient").replace(" ", "_")

        if out_fmt == "pdf":
            img.save(out_buf, format="PDF", resolution=150.0)
            mime = "application/pdf"
            filename = f"{cert_id}_{safe_name}.pdf"
        else:
            img.save(out_buf, format="PNG", optimize=True)
            mime = "image/png"
            filename = f"{cert_id}_{safe_name}.png"

        return RenderResult(
            content=out_buf.getvalue(),
            filename=filename,
            mime_type=mime,
            metadata={"canvas_size": f"{canvas_w}x{canvas_h}", "format": out_fmt}
        )
