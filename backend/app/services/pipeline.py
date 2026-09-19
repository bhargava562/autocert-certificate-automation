"""
Certificate Pipeline Orchestrator
Coordinates the end-to-end rendering and storage workflow via Dependency Injection.
Does not know about filesystem or Supabase internals.
"""

from typing import List, Dict, Any
from .protocols import TemplateProvider, StorageSink
from .models import TemplateManifest
from .engines.factory import CertificateEngineFactory

class CertificatePipeline:
    """Orchestrates certificate generation and persistence across decoupled components"""

    def __init__(
        self,
        template_provider: TemplateProvider,
        engine_factory: CertificateEngineFactory,
        storage_sink: StorageSink
    ):
        self.template_provider = template_provider
        self.engine_factory = engine_factory
        self.storage_sink = storage_sink

    def generate_one(
        self,
        template_id: str,
        participant: Dict[str, Any],
        manifest: TemplateManifest
    ) -> str:
        """Generates a single certificate and persists it to the storage sink"""
        template_bytes = self.template_provider.get_template_bytes(template_id)
        template_name = self.template_provider.get_template_name(template_id)

        engine = self.engine_factory.get_engine_for(template_name)
        result = engine.render(template_bytes, participant, manifest)

        saved_location = self.storage_sink.save(
            content=result.content,
            filename=result.filename,
            mime_type=result.mime_type
        )
        return saved_location

    def generate_batch(
        self,
        template_id: str,
        participants: List[Dict[str, Any]],
        manifest: TemplateManifest
    ) -> List[str]:
        """Generates certificates for a batch of participants"""
        # Fetch template once into memory for the whole batch
        template_bytes = self.template_provider.get_template_bytes(template_id)
        template_name = self.template_provider.get_template_name(template_id)
        engine = self.engine_factory.get_engine_for(template_name)

        output_locations = []
        for p in participants:
            result = engine.render(template_bytes, p, manifest)
            loc = self.storage_sink.save(
                content=result.content,
                filename=result.filename,
                mime_type=result.mime_type
            )
            output_locations.append(loc)

        return output_locations
