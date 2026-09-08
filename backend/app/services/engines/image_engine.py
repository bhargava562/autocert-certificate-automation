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
            val = fields.get(field_name)
            if val is None:
                # Check known synonym mappings for template flexibility
                if field_name in ("recipient_name", "name"):
                    val = fields.get("recipient_name") or fields.get("name")
                elif field_name in ("role", "achievement_title", "title"):
                    val = fields.get("role") or fields.get("achievement_title") or fields.get("title")
                elif field_name in ("date", "issue_date"):
                    val = fields.get("issue_date") or fields.get("date")

            if val is None:
                continue
            text_str = str(val).strip()
            if not text_str:
                continue

            if config.clear_area and config.clear_bg_color:
                x1 = int(canvas_w * config.clear_area[0])
                y1 = int(canvas_h * config.clear_area[1])
                x2 = int(canvas_w * config.clear_area[2])
                y2 = int(canvas_h * config.clear_area[3])
                draw.rectangle([(x1, y1), (x2, y2)], fill=config.clear_bg_color)
            elif field_name in ("recipient_name", "name"):
                # Default safety wipe for recipient slot scaled dynamically
                draw.rectangle(
                    [(int(canvas_w * 0.20), int(canvas_h * 0.38)), (int(canvas_w * 0.80), int(canvas_h * 0.505))],
                    fill=(255, 255, 255)
                )

            max_width = int(canvas_w * config.max_w_pct)
            target_size = max(10, int(canvas_h * config.font_size_pct))
            min_size = (
                max(8, int(canvas_h * config.min_font_size_pct))
                if getattr(config, "min_font_size_pct", None)
                else config.min_font_size
            )

            # Handle multi-line vs single-line
            if len(text_str) > 70 or "\n" in text_str or config.font_size_pct <= 0.035:
                # Body / paragraph text (e.g. achievement description)
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
                        line_x = self.text_service.calculate_center_x(canvas_w, line_w)
                    elif config.align == "right":
                        line_x = int(canvas_w * config.x_pct) - line_w
                    else:
                        line_x = int(canvas_w * config.x_pct)

                    draw.text((line_x, curr_y), line, font=font, fill=config.color)
                    curr_y += line_height
            else:
                # Single-line prominent text (e.g. recipient_name)
                font, actual_size, text_w = self.text_service.fit_text_to_width(
                    draw=draw,
                    text=text_str,
                    font_family=config.font_family,
                    target_size=target_size,
                    max_width=max_width,
                    min_size=min_size
                )

                if config.align == "center":
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
        safe_name = fields.get("recipient_name", "recipient").replace(" ", "_")

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
