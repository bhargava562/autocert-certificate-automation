"""
Template Placeholder Scanner Service
Scans uploaded certificate template bytes (PDF or Image) for placeholder strings
(e.g., {{name}}, {{year}}, {{dept}}, {{full_name}}, {{department}}).
Handles Canva-exported PDFs by:
- Filtering out rotated/diagonal watermark text spans.
- Reconstructing split {{...}} tokens across adjacent spans on the same baseline.
- Computing exact available horizontal slot bounds between neighboring static words
  so injected values never collide with surrounding text (e.g., 'of', 'Year', 'in').
"""

import re
from typing import Dict, List, Optional, Tuple
import pymupdf
from .models import TemplateManifest, FieldConfig

PLACEHOLDER_SYNONYMS = {
    "full_name": ["{{name}}", "{{full_name}}", "{{recipient_name}}", "[name]", "<name>", "{{NAME}}"],
    "year": ["{{year}}", "{{class}}", "{{academic_year}}", "[year]", "<year>", "{{YEAR}}"],
    "department": ["{{dept}}", "{{department}}", "{{branch}}", "[dept]", "<dept>", "{{DEPT}}"],
    "achievement_title": ["{{event}}", "{{title}}", "{{achievement_title}}", "[title]"],
}

_PLACEHOLDER_RE = re.compile(
    r"(\{\{[^}]+\}\}|\[\[[^\]]+\]\]|\[(?:name|year|dept|title)\]|<(?:name|year|dept)>)",
    re.IGNORECASE,
)

_ALIAS_TO_KEY = {
    "name": "full_name",
    "full_name": "full_name",
    "recipient_name": "full_name",
    "year": "year",
    "class": "year",
    "academic_year": "year",
    "dept": "department",
    "department": "department",
    "branch": "department",
    "event": "achievement_title",
    "title": "achievement_title",
    "achievement_title": "achievement_title",
}


def _normalize_token_key(token_str: str) -> str:
    """Normalizes a raw placeholder token like '{{Full Name}}' or '[[dept]]' to a canonical key."""
    inner = token_str.strip()
    for left, right in (("{{", "}}"), ("[[", "]]"), ("[", "]"), ("<", ">")):
        if inner.startswith(left) and inner.endswith(right):
            inner = inner[len(left) : -len(right)]
            break
    norm = re.sub(r"[^a-z0-9]+", "_", inner.strip().lower()).strip("_")
    return _ALIAS_TO_KEY.get(norm, norm or "field")


def _extract_span_style(spans: List[Dict]) -> Tuple[Optional[float], bool, bool, str, str]:
    """Extracts (font_size_pt, bold, italic, font_family, hex_color) from matched spans."""
    if not spans:
        return None, False, False, "sans-serif", "#111827"

    # Prefer a span containing alphanumeric token characters (not just '{{' or '}}')
    primary = spans[0]
    for s in spans:
        if any(ch.isalnum() for ch in s.get("text", "")):
            primary = s
            break

    font_name = str(primary.get("font", "") or "")
    font_l = font_name.lower()
    flags = int(primary.get("flags", 0) or 0)

    bold = bool(flags & 16) or any(
        k in font_l for k in ("bold", "black", "heavy", "semibold", "demibold", "demi")
    )
    italic = bool(flags & 2) or any(
        k in font_l for k in ("italic", "oblique", "slant")
    )

    if any(k in font_l for k in ("times", "serif", "georgia", "garamond", "palatino", "cinzel")):
        font_family = "serif"
    elif any(k in font_l for k in ("script", "cursive", "brush", "greatvibes", "dancing")):
        font_family = "script"
    else:
        font_family = "sans-serif"

    color_val = primary.get("color")
    if isinstance(color_val, int):
        hex_color = f"#{color_val & 0xFFFFFF:06x}"
    else:
        hex_color = "#111827"

    span_size = primary.get("size")
    size_pt = float(span_size) if span_size is not None else None
    return size_pt, bold, italic, font_family, hex_color


def _match_rect_on_line(
    page: pymupdf.Page,
    token_str: str,
    spans_with_offsets: List[Tuple[int, int, Dict]],
    match_start: int,
    match_end: int,
    line_bbox: Tuple[float, float, float, float],
) -> Optional[pymupdf.Rect]:
    """Computes the exact bounding box for a placeholder match on a horizontal line."""
    overlapping_spans = [
        (s_start, s_end, s)
        for s_start, s_end, s in spans_with_offsets
        if s_end > match_start and s_start < match_end
    ]
    if not overlapping_spans:
        return None

    x0s, y0s, x1s, y1s = [], [], [], []
    for s_start, s_end, s in overlapping_spans:
        sx0, sy0, sx1, sy1 = s["bbox"]
        stext = s.get("text", "")
        slen = max(1, len(stext))
        char_w = (sx1 - sx0) / slen
        ov_start = max(match_start, s_start) - s_start
        ov_end = min(match_end, s_end) - s_start
        x0s.append(sx0 + ov_start * char_w)
        x1s.append(sx0 + ov_end * char_w)
        y0s.append(sy0)
        y1s.append(sy1)

    interp_rect = pymupdf.Rect(min(x0s), min(y0s), max(x1s), max(y1s))
    line_cy = (line_bbox[1] + line_bbox[3]) / 2.0

    # Prefer PyMuPDF's exact search_for rect if it falls on this same horizontal line
    for cand in page.search_for(token_str):
        cand_cy = (cand.y0 + cand.y1) / 2.0
        if abs(cand_cy - line_cy) <= max(4.0, (line_bbox[3] - line_bbox[1]) * 0.8):
            if cand.x1 >= interp_rect.x0 - 4.0 and cand.x0 <= interp_rect.x1 + 4.0:
                return cand

    return interp_rect


def _is_horizontal_line(line: Dict) -> bool:
    """Returns True for normal horizontal text lines, filtering out angled/diagonal watermarks."""
    dx, dy = line.get("dir", (1.0, 0.0))
    return abs(dx - 1.0) <= 0.05 and abs(dy) <= 0.05


def _collect_horizontal_tokens(page: pymupdf.Page) -> Tuple[List[Dict], List[Tuple[float, float, float, float, str]]]:
    """
    Extracts horizontal spans (merging adjacent spans on the same line) and
    non-placeholder static word boxes for slot-boundary calculation.
    """
    text_dict = page.get_text("dict")
    line_records: List[Dict] = []

    for block in text_dict.get("blocks", []):
        for line in block.get("lines", []):
            if not _is_horizontal_line(line):
                continue
            spans = line.get("spans", [])
            if not spans:
                continue
            full_text = "".join(s.get("text", "") for s in spans)
            line_records.append({
                "bbox": line["bbox"],
                "text": full_text,
                "spans": spans,
            })

    # Extract word boxes that lie on horizontal lines (exclude diagonal watermark words)
    static_words: List[Tuple[float, float, float, float, str]] = []
    for w in page.get_text("words"):
        wx0, wy0, wx1, wy1, wtext = float(w[0]), float(w[1]), float(w[2]), float(w[3]), str(w[4])
        wcy = (wy0 + wy1) / 2.0
        on_horizontal = any(
            lr["bbox"][1] - 2.0 <= wcy <= lr["bbox"][3] + 2.0
            and wx0 >= lr["bbox"][0] - 2.0
            and wx1 <= lr["bbox"][2] + 2.0
            for lr in line_records
        )
        if not on_horizontal:
            continue
        if _PLACEHOLDER_RE.fullmatch(wtext.strip()):
            continue
        # If a word fuses placeholder + static text (e.g. '{{year}}Year'), keep only static part
        if _PLACEHOLDER_RE.search(wtext):
            continue
        static_words.append((wx0, wy0, wx1, wy1, wtext))

    # Also add non-placeholder span fragments (e.g. 'Year ' when fused in get_text('words'))
    for lr in line_records:
        for s in lr["spans"]:
            stext = s.get("text", "")
            stripped = stext.strip()
            if not stripped or _PLACEHOLDER_RE.search(stripped):
                continue
            sx0, sy0, sx1, sy1 = s["bbox"]
            # Trim leading/trailing space approximation when span has padding spaces
            if len(stext) > 0:
                char_w = (sx1 - sx0) / len(stext)
                lead = len(stext) - len(stext.lstrip())
                trail = len(stext) - len(stext.rstrip())
                sx0_trim = sx0 + lead * char_w
                sx1_trim = sx1 - trail * char_w
                if sx1_trim > sx0_trim:
                    static_words.append((sx0_trim, sy0, sx1_trim, sy1, stripped))

    return line_records, static_words


def _find_slot_bounds(
    occ: pymupdf.Rect,
    pw: float,
    static_words: List[Tuple[float, float, float, float, str]],
    field_key: str,
) -> Tuple[float, float, float, int]:
    """
    Computes (center_x_pct, max_w_pct, font_size_hint, max_lines) for a placeholder rect.
    When static words sit on the same baseline to the left/right, clamps the slot
    strictly between them with a breathing margin and sets max_lines=1 so inline
    values shrink cleanly onto a single line without wrapping over adjacent text.
    """
    cy = (occ.y0 + occ.y1) / 2.0
    tol_y = max(4.0, (occ.y1 - occ.y0) * 0.8)

    left_edge: Optional[float] = None
    right_edge: Optional[float] = None

    for wx0, wy0, wx1, wy1, _ in static_words:
        wcy = (wy0 + wy1) / 2.0
        if abs(wcy - cy) > tol_y:
            continue
        if wx1 <= occ.x0 + 1.5:
            if left_edge is None or wx1 > left_edge:
                left_edge = wx1
        elif wx0 >= occ.x1 - 1.5:
            if right_edge is None or wx0 < right_edge:
                right_edge = wx0

    margin = max(2.5, (occ.y1 - occ.y0) * 0.3)
    if left_edge is not None and right_edge is not None and right_edge - left_edge > (occ.x1 - occ.x0):
        slot_x0 = left_edge + margin
        slot_x1 = right_edge - margin
        center_x = ((slot_x0 + slot_x1) / 2.0) / pw
        max_w = max(0.04, (slot_x1 - slot_x0) / pw)
        return center_x, max_w, (occ.y1 - occ.y0), 1

    # Standalone placeholder (no inline neighbors on both sides)
    center_x = ((occ.x0 + occ.x1) / 2.0) / pw
    raw_w_pct = (occ.x1 - occ.x0) / pw
    if field_key == "full_name":
        max_w = max(0.45, min(0.80, raw_w_pct * 4.0))
    elif field_key == "achievement_title":
        max_w = max(0.40, min(0.75, raw_w_pct * 3.5))
    elif field_key == "department":
        max_w = max(0.18, min(0.45, raw_w_pct * 2.5))
    elif field_key == "year":
        max_w = max(0.10, min(0.25, raw_w_pct * 2.0))
    else:
        max_w = max(0.25, min(0.65, raw_w_pct * 3.0))

    return center_x, max_w, (occ.y1 - occ.y0), 3


def _field_to_placeholder_detail(field_key: str, cfg: FieldConfig) -> Dict:
    """Converts a FieldConfig into an extracted placeholder metadata dictionary."""
    return {
        "key": field_key,
        "token": cfg.token or f"{{{{{field_key}}}}}",
        "label": field_key.replace("_", " ").title(),
        "font_size_pct": cfg.font_size_pct,
        "bold": bool(cfg.bold),
        "italic": bool(cfg.italic),
        "color": cfg.color,
        "max_lines": cfg.max_lines,
        "required": bool(cfg.required or field_key == "full_name"),
    }


def scan_template_details(
    template_bytes: bytes,
    filename: str,
    default_format: str = "png",
) -> Tuple[TemplateManifest, List[Dict]]:
    """
    Scans PDF or image template for any {{token}}, [[token]], [name]/[year]/[dept]/[title],
    or <name>/<year>/<dept> placeholders on horizontal lines (ignoring diagonal watermarks).
    Merges split spans across the same baseline, extracts font size, bold, italic, and hex color,
    and returns (TemplateManifest, extracted_placeholders).
    """
    fn_lower = filename.lower()
    ext = fn_lower.split(".")[-1]

    found_fields: Dict[str, FieldConfig] = {}
    extracted_placeholders: List[Dict] = []

    try:
        if ext == "pdf":
            doc = pymupdf.open(stream=template_bytes, filetype="pdf")
        else:
            img_doc = pymupdf.open(stream=template_bytes, filetype=ext)
            pdf_bytes = img_doc.convert_to_pdf()
            doc = pymupdf.open(stream=pdf_bytes, filetype="pdf")
            img_doc.close()

        if doc.page_count > 0:
            page = doc[0]
            pw = page.rect.width
            ph = page.rect.height
            line_records, static_words = _collect_horizontal_tokens(page)

            for lr in line_records:
                full_text = lr["text"]
                if not full_text:
                    continue

                spans_with_offsets: List[Tuple[int, int, Dict]] = []
                cursor = 0
                for sp in lr["spans"]:
                    stext = sp.get("text", "")
                    spans_with_offsets.append((cursor, cursor + len(stext), sp))
                    cursor += len(stext)

                for match in _PLACEHOLDER_RE.finditer(full_text):
                    token_str = match.group(0)
                    field_key = _normalize_token_key(token_str)
                    if field_key in found_fields:
                        continue

                    m_start, m_end = match.start(), match.end()
                    overlapping = [
                        s for s_start, s_end, s in spans_with_offsets
                        if s_end > m_start and s_start < m_end
                    ]
                    r = _match_rect_on_line(
                        page, token_str, spans_with_offsets, m_start, m_end, lr["bbox"]
                    )
                    if r is None or pw <= 0 or ph <= 0:
                        continue

                    size_pt, bold, italic, font_family, hex_color = _extract_span_style(overlapping)
                    center_x, max_w, token_h, slot_max_lines = _find_slot_bounds(
                        r, pw, static_words, field_key
                    )
                    center_y = ((r.y0 + r.y1) / 2.0) / ph

                    x1_pct = max(0.0, r.x0 / pw)
                    y1_pct = max(0.0, r.y0 / ph)
                    x2_pct = min(1.0, r.x1 / pw)
                    y2_pct = min(1.0, r.y1 / ph)

                    raw_size = size_pt if size_pt and size_pt > 0 else token_h
                    font_size_pct = round(raw_size / ph, 4)
                    if font_size_pct < 0.010:
                        font_size_pct = 0.026

                    is_required = field_key == "full_name"
                    cfg = FieldConfig(
                        name=field_key,
                        x_pct=round(center_x, 4),
                        y_pct=round(center_y, 4),
                        max_w_pct=round(max_w, 4),
                        max_lines=slot_max_lines,
                        font_family=font_family,
                        font_size_pct=font_size_pct,
                        min_font_size_pct=round(max(0.012, font_size_pct * 0.55), 4),
                        align="center",
                        color=hex_color,
                        clear_area=(round(x1_pct, 4), round(y1_pct, 4), round(x2_pct, 4), round(y2_pct, 4)),
                        clear_bg_color="transparent",
                        bold=bold,
                        italic=italic,
                        token=token_str,
                        required=is_required,
                    )
                    found_fields[field_key] = cfg
                    extracted_placeholders.append(_field_to_placeholder_detail(field_key, cfg))

            doc.close()
    except Exception:
        pass

    if found_fields:
        manifest = TemplateManifest(
            template_id="scanned_placeholder_manifest",
            template_filename=filename,
            default_format=default_format,
            base_width=2000,
            base_height=1414,
            fields=found_fields,
        )
        return manifest, extracted_placeholders

    fallback_fields = {
        "full_name": FieldConfig(
            name="full_name",
            x_pct=0.470,
            y_pct=0.592,
            max_w_pct=0.175,
            font_family="sans-serif",
            font_size_pct=0.024,
            min_font_size_pct=0.012,
            align="center",
            color="#0f172a",
            clear_area=(0.420, 0.550, 0.535, 0.635),
            clear_bg_color="transparent",
            token="{{full_name}}",
            required=True,
        ),
        "year": FieldConfig(
            name="year",
            x_pct=0.625,
            y_pct=0.592,
            max_w_pct=0.070,
            font_family="sans-serif",
            font_size_pct=0.024,
            min_font_size_pct=0.012,
            align="center",
            color="#0f172a",
            clear_area=(0.595, 0.550, 0.672, 0.635),
            clear_bg_color="transparent",
            token="{{year}}",
            required=False,
        ),
        "department": FieldConfig(
            name="department",
            x_pct=0.748,
            y_pct=0.592,
            max_w_pct=0.075,
            font_family="sans-serif",
            font_size_pct=0.024,
            min_font_size_pct=0.012,
            align="center",
            color="#0f172a",
            clear_area=(0.715, 0.550, 0.800, 0.635),
            clear_bg_color="transparent",
            token="{{department}}",
            required=False,
        ),
    }
    fallback_manifest = TemplateManifest(
        template_id="rmk_participation_manifest",
        template_filename=filename,
        default_format=default_format,
        base_width=2000,
        base_height=1414,
        fields=fallback_fields,
    )
    fallback_placeholders = [
        _field_to_placeholder_detail(k, cfg) for k, cfg in fallback_fields.items()
    ]
    return fallback_manifest, fallback_placeholders


def scan_template_placeholders(template_bytes: bytes, filename: str, default_format: str = "png") -> TemplateManifest:
    """
    Scans document template for exact or split placeholder occurrences.
    Filters out diagonal/rotated watermark text and computes slot-constrained
    FieldConfig bounding boxes. Falls back to calibrated manifest if none found.
    """
    manifest, _ = scan_template_details(template_bytes, filename, default_format=default_format)
    return manifest
