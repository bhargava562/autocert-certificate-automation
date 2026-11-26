"""
Text Fitting & Layout Service
Eliminates arbitrary coordinates by calculating exact bounding boxes,
dynamic font auto-scaling, horizontal auto-centering, and word wrapping.
"""

import os
from typing import Tuple, List, Optional
from PIL import ImageFont, ImageDraw, Image

class TextFittingService:
    """Service to measure, auto-scale, and center text on dynamic layouts"""

    def __init__(self, custom_font_dir: Optional[str] = None):
        self.custom_font_dir = custom_font_dir or os.path.join(
            os.path.dirname(__file__), "..", "..", "assets", "fonts"
        )
        self._font_cache = {}

    def get_font_path(self, font_family: str) -> Optional[str]:
        """Resolves font path from custom assets, Windows system fonts, or fallbacks, honoring bold weight."""
        font_family = font_family.lower()
        wants_bold = "bold" in font_family

        # 1. Check custom assets folder
        if os.path.exists(self.custom_font_dir):
            files = [fn for fn in os.listdir(self.custom_font_dir) if fn.endswith((".ttf", ".otf"))]
            if wants_bold:
                for fn in files:
                    fn_l = fn.lower()
                    if "bold" in fn_l and (font_family.replace("-bold", "").replace("bold", "").strip() in fn_l or "sans" in font_family):
                        return os.path.join(self.custom_font_dir, fn)
            for fn in files:
                if font_family in fn.lower():
                    return os.path.join(self.custom_font_dir, fn)

        # 2. Check Windows System Fonts
        win_fonts = r"C:\Windows\Fonts"
        if os.path.exists(win_fonts):
            if "script" in font_family or "cursive" in font_family:
                candidates = ["segoescb.ttf", "segoesc.ttf", "FRSCRIPT.TTF", "SCRIPTBL.TTF", "georgia.ttf"] if wants_bold else ["segoesc.ttf", "FRSCRIPT.TTF", "SCRIPTBL.TTF", "georgia.ttf"]
            elif "serif" in font_family or "times" in font_family or "cinzel" in font_family:
                candidates = ["timesbd.ttf", "georgiab.ttf", "times.ttf", "georgia.ttf", "pala.ttf"] if wants_bold else ["times.ttf", "georgia.ttf", "pala.ttf", "arial.ttf"]
            else:
                candidates = ["arialbd.ttf", "calibrib.ttf", "segoeuib.ttf", "arial.ttf", "calibri.ttf", "segoeui.ttf"] if wants_bold else ["arial.ttf", "calibri.ttf", "segoeui.ttf"]

            for cand in candidates:
                cand_path = os.path.join(win_fonts, cand)
                if os.path.exists(cand_path):
                    return cand_path

        return None

    def load_font(self, font_family: str, size: int) -> ImageFont.FreeTypeFont:
        """Loads a font at the requested size, falling back safely if not found"""
        cache_key = (font_family, size)
        if cache_key in self._font_cache:
            return self._font_cache[cache_key]

        font_path = self.get_font_path(font_family)
        if font_path and os.path.exists(font_path):
            try:
                font = ImageFont.truetype(font_path, size)
                self._font_cache[cache_key] = font
                return font
            except Exception:
                pass

        try:
            font = ImageFont.truetype("arial.ttf", size)
        except Exception:
            font = ImageFont.load_default()

        self._font_cache[cache_key] = font
        return font

    @staticmethod
    def fit_font_size_binary_search(
        text: str,
        measure_fn,
        max_width: int,
        min_font: int,
        max_font: int,
    ) -> Tuple[int, int]:
        """
        Deterministic O(log(max_font - min_font)) binary search for the largest font size
        in [min_font, max_font] where measure_fn(text, size) <= max_width.
        Returns (best_size, measured_width).
        """
        if max_font <= min_font:
            return min_font, measure_fn(text, min_font)

        low = min_font
        high = max_font
        best_size = min_font
        best_width = measure_fn(text, min_font)

        while low <= high:
            mid = (low + high) // 2
            w = measure_fn(text, mid)
            if w <= max_width:
                best_size = mid
                best_width = w
                low = mid + 1
            else:
                high = mid - 1

        return best_size, best_width

    def fit_text_to_width(
        self,
        draw: ImageDraw.ImageDraw,
        text: str,
        font_family: str,
        target_size: int,
        max_width: int,
        min_size: int = 18
    ) -> Tuple[ImageFont.FreeTypeFont, int, int]:
        """
        Dynamically auto-scales font size using binary search until text fits within max_width.
        Returns: (fitted_font, actual_font_size, text_width)
        """
        def _measure(txt: str, sz: int) -> int:
            font = self.load_font(font_family, sz)
            bbox = draw.textbbox((0, 0), txt, font=font)
            return bbox[2] - bbox[0]

        best_size, best_width = self.fit_font_size_binary_search(
            text=text,
            measure_fn=_measure,
            max_width=max_width,
            min_font=min_size,
            max_font=max(min_size, target_size),
        )
        return self.load_font(font_family, best_size), best_size, best_width

    def measure_text_width(
        self,
        draw: ImageDraw.ImageDraw,
        text: str,
        font: ImageFont.FreeTypeFont,
    ) -> int:
        """Measures rendered pixel width of a single line of text."""
        if not text:
            return 0
        bbox = draw.textbbox((0, 0), text, font=font)
        return bbox[2] - bbox[0]

    def calculate_center_x(self, canvas_width: int, text_width: int) -> int:
        """Calculates precise horizontal center coordinate"""
        return max(0, int((canvas_width - text_width) / 2))

    def compute_vertical_start_y(
        self,
        anchor_y: int,
        total_height: int,
        v_align: str = "center",
        box_top: Optional[int] = None,
        box_bottom: Optional[int] = None,
    ) -> int:
        """Computes starting Y coordinate for a text block based on v_align (top|center|bottom)."""
        align_mode = (v_align or "center").lower()
        if align_mode == "top":
            return box_top if box_top is not None else anchor_y
        if align_mode == "bottom":
            return (box_bottom - total_height) if box_bottom is not None else (anchor_y - total_height)
        return anchor_y - (total_height // 2)

    def ellipsize_line(
        self,
        draw: ImageDraw.ImageDraw,
        text: str,
        font: ImageFont.FreeTypeFont,
        max_width: int,
        suffix: str = "...",
    ) -> str:
        """Truncates a line with ellipsis so its rendered width fits within max_width."""
        if self.measure_text_width(draw, text, font) <= max_width:
            return text
        if self.measure_text_width(draw, suffix, font) > max_width:
            return suffix

        trimmed = text.rstrip()
        if trimmed.endswith(suffix):
            trimmed = trimmed[:-len(suffix)].rstrip()

        while trimmed and self.measure_text_width(draw, trimmed + suffix, font) > max_width:
            trimmed = trimmed[:-1]

        return (trimmed.rstrip() + suffix) if trimmed else suffix

    def wrap_text(
        self,
        draw: ImageDraw.ImageDraw,
        text: str,
        font: ImageFont.FreeTypeFont,
        max_width: int
    ) -> List[str]:
        """Wraps text cleanly across multiple lines within max_width, preserving explicit newlines."""
        lines: List[str] = []
        paragraphs = text.splitlines() or [text]

        for paragraph in paragraphs:
            words = paragraph.split()
            if not words:
                lines.append("")
                continue

            current_line: List[str] = []
            for word in words:
                test_line = " ".join(current_line + [word])
                if self.measure_text_width(draw, test_line, font) <= max_width:
                    current_line.append(word)
                else:
                    if current_line:
                        lines.append(" ".join(current_line))
                    current_line = [word]

            if current_line:
                lines.append(" ".join(current_line))

        return lines

    def fit_text_block(
        self,
        draw: ImageDraw.ImageDraw,
        text: str,
        font_family: str,
        target_size: int,
        max_width: int,
        max_height: Optional[int] = None,
        min_size: int = 18,
        max_lines: int = 3,
        line_spacing: float = 1.3,
        overflow_policy: str = "shrink_wrap",
        force_multiline: bool = False,
        field_name: str = "field",
    ) -> Tuple[ImageFont.FreeTypeFont, int, List[str], int, bool, List[str]]:
        """
        Fits text into a (max_width, max_height, max_lines) bounding box.
        Returns: (font, actual_size, lines, line_height, overflowed, warnings)
        """
        allowed_lines = max(1, int(max_lines or 1))
        policy = (overflow_policy or "shrink_wrap").lower()

        # 1. Try single-line fit first when multiline is not forced
        if not force_multiline and "\n" not in text:
            font, actual_size, text_w = self.fit_text_to_width(
                draw=draw,
                text=text,
                font_family=font_family,
                target_size=target_size,
                max_width=max_width,
                min_size=min_size,
            )
            line_height = max(1, int(actual_size * line_spacing))
            if text_w <= max_width and (max_height is None or line_height <= max_height):
                return font, actual_size, [text], line_height, False, []

            if text_w <= max_width and max_height is not None and line_height > max_height:
                step = max(1, int(target_size * 0.025))
                size = actual_size
                while size >= min_size:
                    lh = max(1, int(size * line_spacing))
                    if lh <= max_height:
                        return self.load_font(font_family, size), size, [text], lh, False, []
                    size -= step

        # 2. If single-line is strictly required under flag_overflow, flag immediately
        if policy == "flag_overflow" and allowed_lines == 1:
            font = self.load_font(font_family, min_size)
            line_height = max(1, int(min_size * line_spacing))
            warning = f"Field '{field_name}' exceeds single-line bounds at min font size ({min_size}px)"
            return font, min_size, [text], line_height, True, [warning]

        # 3. Multi-line wrapping mode with adaptive downscaling
        wrap_size = target_size
        wrap_step = max(1, int(target_size * 0.04))

        while wrap_size >= min_size:
            font = self.load_font(font_family, wrap_size)
            lines = self.wrap_text(draw, text, font, max_width)
            line_height = max(1, int(wrap_size * line_spacing))
            total_text_h = len(lines) * line_height

            fits_lines = len(lines) <= allowed_lines
            fits_height = max_height is None or total_text_h <= max_height
            fits_width = all(self.measure_text_width(draw, ln, font) <= max_width for ln in lines)

            if fits_lines and fits_height and fits_width:
                return font, wrap_size, lines, line_height, False, []

            wrap_size -= wrap_step

        # 4. Re-evaluate exactly at min_size
        font = self.load_font(font_family, min_size)
        lines = self.wrap_text(draw, text, font, max_width)
        line_height = max(1, int(min_size * line_spacing))
        total_text_h = len(lines) * line_height

        fits_lines = len(lines) <= allowed_lines
        fits_height = max_height is None or total_text_h <= max_height
        fits_width = all(self.measure_text_width(draw, ln, font) <= max_width for ln in lines)

        if fits_lines and fits_height and fits_width:
            return font, min_size, lines, line_height, False, []

        # 5. Text still exceeds bounds at min_size -> apply overflow_policy
        if policy == "ellipsize":
            allowed_by_h = max(1, max_height // line_height) if max_height is not None else allowed_lines
            effective_max_lines = max(1, min(allowed_lines, allowed_by_h))
            truncated = len(lines) > effective_max_lines
            lines = lines[:effective_max_lines]

            if truncated and lines:
                candidate = lines[-1].rstrip() + "..."
                lines[-1] = (
                    self.ellipsize_line(draw, candidate, font, max_width)
                    if self.measure_text_width(draw, candidate, font) > max_width
                    else candidate
                )

            lines = [
                self.ellipsize_line(draw, ln, font, max_width)
                if self.measure_text_width(draw, ln, font) > max_width
                else ln
                for ln in lines
            ]
            warning = f"Field '{field_name}' truncated with ellipsis at min font size ({min_size}px)"
            return font, min_size, lines, line_height, True, [warning]

        warning = (
            f"Field '{field_name}' exceeds bounds at min font size ({min_size}px): "
            f"{len(lines)} lines (max {allowed_lines}), height {total_text_h}px (max {max_height}px)"
        )
        return font, min_size, lines, line_height, True, [warning]
