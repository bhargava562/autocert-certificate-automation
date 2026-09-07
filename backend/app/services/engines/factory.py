"""
Certificate Engine Factory
Resolves the appropriate rendering engine for any given template file type.
Follows Open/Closed Principle: new format engines can be registered dynamically.
"""

from typing import List
from ..protocols import CertificateEngine
from ..text_fitting import TextFittingService
from .image_engine import PillowImageEngine
from .pdf_engine import PyMuPdfEngine
from .docx_engine import DocxTemplateEngine

class CertificateEngineFactory:
    """Factory to resolve or register CertificateEngine instances"""

    def __init__(self, text_service: TextFittingService):
        self.text_service = text_service
        self._engines: List[CertificateEngine] = [
            PillowImageEngine(self.text_service),
            PyMuPdfEngine(),
            DocxTemplateEngine()
        ]

    def register_engine(self, engine: CertificateEngine) -> None:
        """Register a custom engine (Open/Closed Principle)"""
        self._engines.insert(0, engine)

    def get_engine_for(self, filename_or_ext: str) -> CertificateEngine:
        """Returns the first engine that can handle the given file extension"""
        for engine in self._engines:
            if engine.can_handle(filename_or_ext):
                return engine
        raise ValueError(f"No suitable certificate engine found for '{filename_or_ext}'")
