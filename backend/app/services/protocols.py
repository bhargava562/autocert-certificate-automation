"""
Protocol Interfaces (SOLID Abstractions)
Enables structural subtyping, dependency inversion, and zero coupling.
"""

from typing import Protocol, Dict, Any, runtime_checkable
from .models import TemplateManifest, RenderResult

@runtime_checkable
class TemplateProvider(Protocol):
    """Responsible for fetching template assets (local or remote)"""
    def get_template_bytes(self, template_id: str) -> bytes:
        ...

    def get_template_name(self, template_id: str) -> str:
        ...

@runtime_checkable
class CertificateEngine(Protocol):
    """Responsible for rendering dynamic fields onto template bytes"""
    def can_handle(self, filename_or_ext: str) -> bool:
        ...

    def render(
        self,
        template_bytes: bytes,
        fields: Dict[str, Any],
        manifest: TemplateManifest
    ) -> RenderResult:
        ...

@runtime_checkable
class StorageSink(Protocol):
    """Responsible for persisting rendered certificates (local or cloud)"""
    def save(self, content: bytes, filename: str, mime_type: str) -> str:
        ...
