"""
Word DOCX Template Certificate Engine
Uses docxtpl with Jinja2 syntax to populate Word certificate templates.
"""

import io
from typing import Dict, Any
from docxtpl import DocxTemplate
from ..protocols import CertificateEngine
from ..models import TemplateManifest, RenderResult

class DocxTemplateEngine:
    """Renders certificates from Word .docx templates using Jinja2 syntax"""

    def can_handle(self, filename_or_ext: str) -> bool:
        ext = filename_or_ext.lower().split(".")[-1]
        return ext == "docx"

    def render(
        self,
        template_bytes: bytes,
        fields: Dict[str, Any],
        manifest: TemplateManifest
    ) -> RenderResult:
        in_buf = io.BytesIO(template_bytes)
        doc = DocxTemplate(in_buf)
        doc.render(fields)

        out_buf = io.BytesIO()
        doc.save(out_buf)

        cert_id = fields.get("certificate_id", "cert")
        safe_name = fields.get("recipient_name", "recipient").replace(" ", "_")
        filename = f"{cert_id}_{safe_name}.docx"

        return RenderResult(
            content=out_buf.getvalue(),
            filename=filename,
            mime_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
            metadata={"format": "docx"}
        )
