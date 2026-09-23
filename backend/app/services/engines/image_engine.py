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

            max_width = int(canvas_w * config.max_w_pct)
            target_size = max(10, int(canvas_h * config.font_size_pct))
            min_size = (
                max(8, int(canvas_h * config.min_font_size_pct))
                if getattr(config, "min_font_size_pct", None)
                else config.min_font_size
            )

            # Handle multi-line vs single-line
            if len(text_str) > 70 or "\n" in text_str or config.font_size_pct <= 0.020:
                font = self.text_service.load_font(config.font_family, target_size)
                lines = self.text_service.wrap_text(draw, text_str, font, max_width)
                line_height = int(target_size * config.line_spacing)
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
                font, actual_size, text_w = self.text_service.fit_text_to_width(
                    draw=draw,
                    text=text_str,
                    font_family=config.font_family,
                    target_size=target_size,
                    max_width=max_width,
                    min_size=min_size
                )

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
