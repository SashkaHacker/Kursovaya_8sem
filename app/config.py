from __future__ import annotations

import os
from pathlib import Path

APP_TITLE = "OCR Desktop System"

BASE_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = BASE_DIR / "data"
UPLOADS_DIR = BASE_DIR / "uploads"
DB_PATH = DATA_DIR / "ocr_history.db"
STYLE_PATH = BASE_DIR / "app" / "resources" / "style.qss"

DEFAULT_OCR_LANG = "rus+eng"

# If TESSERACT_CMD is set, it has the highest priority.
TESSERACT_CANDIDATES = [
    os.getenv("TESSERACT_CMD", ""),
    r"C:\\Program Files\\Tesseract-OCR\\tesseract.exe",
    r"C:\\Program Files (x86)\\Tesseract-OCR\\tesseract.exe",
]
