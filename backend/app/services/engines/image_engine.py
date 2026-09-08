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
                if field_name in ("recipient_name", "name", "full_name"):
                    val = fields.get("full_name") or fields.get("recipient_name") or fields.get("name")
                elif field_name in ("event_name", "eventname"):
                    val = fields.get("event_name") or fields.get("eventname") or fields.get("achievement_title")
                elif field_name in ("description", "achievement_text"):
                    val = fields.get("achievement_text") or fields.get("description")
                    if not val and fields.get("event_name"):
                        pronoun = "Her" if str(fields.get("gender", "")).lower() == "female" else "His"
                        date_str = fields.get("participated_date") or fields.get("issue_date", "")
                        val = f"has successfully completed {fields.get('event_name')} conducted on {date_str}.\n{pronoun} dedication and commitment to the learning process are truly commendable."
                elif field_name in ("awarded_date", "award_date"):
                    issue_dt = fields.get("issue_date") or fields.get("participated_date", "")
                    val = f"Awarded on {issue_dt}" if issue_dt else None
                elif field_name in ("role", "achievement_title", "title"):
                    val = fields.get("role") or fields.get("achievement_title") or fields.get("title")
                elif field_name in ("date", "issue_date"):
                    val = fields.get("issue_date") or fields.get("date")

            if val is None:
                continue
            text_str = str(val).strip()
            if not text_str:
                continue

            if config.clear_area:
                x1 = int(canvas_w * config.clear_area[0])
                y1 = int(canvas_h * config.clear_area[1])
                x2 = int(canvas_w * config.clear_area[2])
                y2 = int(canvas_h * config.clear_area[3])

                # Determine background fill color
                fill_color = config.clear_bg_color
                if not fill_color or str(fill_color).lower() == "auto":
                    sample_x = min(canvas_w - 1, max(0, x1 + 5))
                    sample_y = min(canvas_h - 1, max(0, y1 + 5))
                    fill_color = img.getpixel((sample_x, sample_y))

                draw.rectangle([(x1, y1), (x2, y2)], fill=fill_color)

                # Defensive line repair for white-green certificate if {{name}} overlapped the line
                t_id = getattr(manifest, "template_id", "").lower()
                t_fn = getattr(manifest, "template_filename", "").lower()
                if ("white" in t_id or "green" in t_id or "completion" in t_id or
                    "white" in t_fn or "green" in t_fn or "completion" in t_fn):
                    line_y = int(canvas_h * 0.488)
                    line_w = max(1, int(canvas_h * 0.0035))
                    draw.line(
                        [(int(canvas_w * 0.35), line_y), (int(canvas_w * 0.65), line_y)],
                        fill=(28, 105, 84),
                        width=line_w
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
