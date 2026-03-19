from __future__ import annotations

import os
from pathlib import Path

import numpy as np
import pytesseract
from pytesseract import TesseractNotFoundError

from app.config import DEFAULT_OCR_LANG, TESSERACT_CANDIDATES


class OCRService:
    def __init__(self, language: str = DEFAULT_OCR_LANG) -> None:
        self.language = language
        self._configure_tesseract_path()

    def _configure_tesseract_path(self) -> None:
        if os.name != "nt":
            return

        for candidate in TESSERACT_CANDIDATES:
            if candidate and Path(candidate).exists():
                pytesseract.pytesseract.tesseract_cmd = candidate
                return

    def extract_text(self, image: np.ndarray) -> str:
        if image is None:
            raise ValueError("Пустое изображение для OCR")

        try:
            text = pytesseract.image_to_string(
                image,
                lang=self.language,
                config="--oem 3 --psm 6",
            )
        except TesseractNotFoundError as exc:
            raise RuntimeError(
                "Tesseract OCR не найден. Установите Tesseract и укажите путь через переменную окружения TESSERACT_CMD."
            ) from exc

        return text.strip()
