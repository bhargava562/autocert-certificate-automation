"""
Local File Template Provider & Local Disk Storage Sink
Supports self-contained, folder-in folder-out local execution.
"""

import os
from ..protocols import TemplateProvider, StorageSink

class LocalTemplateProvider:
    """Reads templates directly from a local directory"""

    def __init__(self, base_dir: str):
        self.base_dir = os.path.abspath(base_dir)

    def _resolve_path(self, template_id: str) -> str:
        # If full path or exact filename
        if os.path.exists(template_id):
            return template_id

        direct_path = os.path.join(self.base_dir, template_id)
        if os.path.exists(direct_path):
            return direct_path

        # Check for matching filename ignoring case or partial
        for fn in os.listdir(self.base_dir):
            if fn.lower() == template_id.lower() or template_id.lower() in fn.lower():
                return os.path.join(self.base_dir, fn)

        raise FileNotFoundError(f"Template '{template_id}' not found in {self.base_dir}")

    def get_template_bytes(self, template_id: str) -> bytes:
        path = self._resolve_path(template_id)
        with open(path, "rb") as f:
            return f.read()

    def get_template_name(self, template_id: str) -> str:
        return os.path.basename(self._resolve_path(template_id))

class LocalDiskSink:
    """Saves generated certificates directly into a local output directory"""

    def __init__(self, output_dir: str):
        self.output_dir = os.path.abspath(output_dir)
        os.makedirs(self.output_dir, exist_ok=True)

    def save(self, content: bytes, filename: str, mime_type: str) -> str:
        dest_path = os.path.join(self.output_dir, filename)
        with open(dest_path, "wb") as f:
            f.write(content)
        return dest_path
