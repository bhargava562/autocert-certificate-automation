"""
Domain Models & Data Structures for Certificate Generation
"""

from dataclasses import dataclass, field
from typing import Dict, Any, Optional

@dataclass
class FieldConfig:
    name: str
    x_pct: float             # 0.0 to 1.0 (relative to template width)
    y_pct: float             # 0.0 to 1.0 (relative to template height)
    max_w_pct: float = 0.70  # Max bounding box width before auto-scaling font down
    font_family: str = "script"  # "script", "serif", "sans-serif"
    font_size_pct: float = 0.055 # Relative font size compared to height
    min_font_size: int = 18      # Lower bound for auto-downscaling
    align: str = "center"        # "left", "center", "right"
    color: str = "#C5A059"       # Hex color code or RGB tuple
    line_spacing: float = 1.3
    anchor_phrase: Optional[str] = None  # For PDF structural text detection

@dataclass
class TemplateManifest:
    template_id: str
    template_filename: str
    default_format: str = "png"  # "png", "pdf", "docx"
    base_width: int = 2000
    base_height: int = 1414
    fields: Dict[str, FieldConfig] = field(default_factory=dict)

@dataclass
class RenderResult:
    content: bytes
    filename: str
    mime_type: str
    metadata: Dict[str, Any] = field(default_factory=dict)
