"""
Domain Models & Data Structures for Certificate Generation
"""

from dataclasses import dataclass, field
from typing import Dict, Any, Optional, Tuple, List

@dataclass
class FieldConfig:
    name: str
    x_pct: float             # 0.0 to 1.0 (relative to dynamic template width)
    y_pct: float             # 0.0 to 1.0 (relative to dynamic template height)
    max_w_pct: float = 0.70  # Max bounding box width relative to dynamic width
    max_h_pct: Optional[float] = None  # Max bounding box height relative to dynamic height
    max_lines: int = 3       # Maximum wrapped lines allowed
    font_family: str = "script"  # "script", "serif", "sans-serif"
    font_size_pct: float = 0.055 # Relative font size compared to height
    min_font_size_pct: float = 0.018 # Dynamic min font size percentage relative to height
    min_font_size: int = 18      # Lower bound fallback in absolute pixels
    align: str = "center"        # "left", "center", "right"
    v_align: str = "center"      # "top", "center", "bottom"
    overflow_policy: str = "shrink_wrap"  # "shrink_wrap", "ellipsize", "flag_overflow"
    color: str = "#C5A059"       # Hex color code or RGB tuple
    line_spacing: float = 1.3
    anchor_phrase: Optional[str] = None  # For PDF structural text detection
    clear_area: Optional[Tuple[float, float, float, float]] = None # (x1_pct, y1_pct, x2_pct, y2_pct)
    clear_bg_color: Optional[str] = None # Fill color to wipe clear_area before rendering (e.g. "#FFFFFF")

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
    overflowed: bool = False
    warnings: List[str] = field(default_factory=list)
