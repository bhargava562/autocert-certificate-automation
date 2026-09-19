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
        """Resolves font path from custom assets, Windows system fonts, or fallbacks"""
        font_family = font_family.lower()

        # 1. Check custom assets folder
        if os.path.exists(self.custom_font_dir):
            for fn in os.listdir(self.custom_font_dir):
                if font_family in fn.lower() and fn.endswith((".ttf", ".otf")):
                    return os.path.join(self.custom_font_dir, fn)

        # 2. Check Windows System Fonts
        win_fonts = r"C:\Windows\Fonts"
        if os.path.exists(win_fonts):
            if "script" in font_family or "cursive" in font_family:
                candidates = ["segoesc.ttf", "FRSCRIPT.TTF", "SCRIPTBL.TTF", "georgia.ttf"]
            elif "serif" in font_family or "times" in font_family or "cinzel" in font_family:
                candidates = ["times.ttf", "georgia.ttf", "pala.ttf", "arial.ttf"]
            else:
                candidates = ["arial.ttf", "calibri.ttf", "segoeui.ttf"]

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
        Dynamically auto-scales font size down until text fits within max_width.
        Returns: (fitted_font, actual_font_size, text_width)
        """
        current_size = target_size
        step = max(1, int(target_size * 0.025))
        while current_size >= min_size:
            font = self.load_font(font_family, current_size)
            bbox = draw.textbbox((0, 0), text, font=font)
            text_width = bbox[2] - bbox[0]
            if text_width <= max_width:
                return font, current_size, text_width
            current_size -= step

        font = self.load_font(font_family, min_size)
        bbox = draw.textbbox((0, 0), text, font=font)
        return font, min_size, bbox[2] - bbox[0]

    def calculate_center_x(self, canvas_width: int, text_width: int) -> int:
        """Calculates precise horizontal center coordinate"""
        return max(0, int((canvas_width - text_width) / 2))

    def wrap_text(
        self,
        draw: ImageDraw.ImageDraw,
        text: str,
        font: ImageFont.FreeTypeFont,
        max_width: int
    ) -> List[str]:
        """Wraps text cleanly across multiple lines within max_width"""
        words = text.split()
        lines = []
        current_line = []

        for word in words:
            test_line = " ".join(current_line + [word])
            bbox = draw.textbbox((0, 0), test_line, font=font)
            if bbox[2] - bbox[0] <= max_width:
                current_line.append(word)
            else:
                if current_line:
                    lines.append(" ".join(current_line))
                current_line = [word]

        if current_line:
            lines.append(" ".join(current_line))

        return lines
