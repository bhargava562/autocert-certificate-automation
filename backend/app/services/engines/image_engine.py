"""
Pillow-Based Image Certificate Engine
Renders text onto flat or raster image templates with dynamic auto-scaling,
exact text centering, and multi-line wrapping.
"""

import io
from typing import Dict, Any, List, Optional
from PIL import Image, ImageDraw
from ..protocols import CertificateEngine
from ..models import TemplateManifest, RenderResult
from ..text_fitting import TextFittingService
from ...core.config import load_settings

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

    def _compute_effective_max_height(self, canvas_h: int, config) -> Optional[int]:
        """Derives the effective maximum pixel height from max_h_pct and clear_area."""
        bounds: List[int] = []
        max_h_pct = getattr(config, "max_h_pct", None)
        if max_h_pct is not None:
            bounds.append(max(1, int(canvas_h * max_h_pct)))
        if config.clear_area:
            clear_h = int(canvas_h * (config.clear_area[3] - config.clear_area[1]))
            if clear_h > 0:
                bounds.append(clear_h)
        return min(bounds) if bounds else None

    def render(
        self,
        template_bytes: bytes,
        fields: Dict[str, Any],
        manifest: TemplateManifest
    ) -> RenderResult:
        # Load image template and configurable defaults
        img = Image.open(io.BytesIO(template_bytes)).convert("RGB")
        draw = ImageDraw.Draw(img)
        canvas_w, canvas_h = img.size
        settings = load_settings()

        any_overflow = False
        render_warnings: List[str] = []

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
            max_height = self._compute_effective_max_height(canvas_h, config)
            target_size = max(10, int(canvas_h * config.font_size_pct))
            min_pct = getattr(config, "min_font_size_pct", None) or settings.default_min_font_size_pct
            min_size = max(8, int(canvas_h * min_pct)) if min_pct else config.min_font_size
            max_lines_allowed = getattr(config, "max_lines", None) or settings.default_max_lines
            v_align = getattr(config, "v_align", "center")
            overflow_policy = getattr(config, "overflow_policy", "shrink_wrap")

            force_multiline = len(text_str) > 70 or "\n" in text_str or config.font_size_pct <= 0.020
            wants_bold = bool(getattr(config, "bold", False))
            wants_italic = bool(getattr(config, "italic", False))

            font, actual_size, lines, line_height, field_overflowed, field_warnings = (
                self.text_service.fit_text_block(
                    draw=draw,
                    text=text_str,
                    font_family=config.font_family,
                    target_size=target_size,
                    max_width=max_width,
                    max_height=max_height,
                    min_size=min_size,
                    max_lines=max_lines_allowed,
                    line_spacing=config.line_spacing,
                    overflow_policy=overflow_policy,
                    force_multiline=force_multiline,
                    field_name=field_name,
                    bold=wants_bold,
                    italic=wants_italic,
                )
            )

            if field_overflowed:
                any_overflow = True
                render_warnings.extend(field_warnings)

            total_text_h = len(lines) * line_height if len(lines) > 1 else actual_size
            box_top = int(canvas_h * config.clear_area[1]) if config.clear_area else None
            box_bottom = int(canvas_h * config.clear_area[3]) if config.clear_area else None
            anchor_y = int(canvas_h * config.y_pct)

            curr_y = self.text_service.compute_vertical_start_y(
                anchor_y=anchor_y,
                total_height=total_text_h,
                v_align=v_align,
                box_top=box_top,
                box_bottom=box_bottom,
            )

            for line in lines:
                line_w = self.text_service.measure_text_width(draw, line, font)
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
            metadata={"canvas_size": f"{canvas_w}x{canvas_h}", "format": out_fmt},
            overflowed=any_overflow,
            warnings=render_warnings,
        )
