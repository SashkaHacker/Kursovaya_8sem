from __future__ import annotations

import sys

from PySide6.QtWidgets import QApplication

from app.config import DATA_DIR, STYLE_PATH, UPLOADS_DIR
from app.ui.main_window import MainWindow
from app.utils.file_utils import ensure_directories


def main() -> int:
    ensure_directories(DATA_DIR, UPLOADS_DIR)

    app = QApplication(sys.argv)
    if STYLE_PATH.exists():
        app.setStyleSheet(STYLE_PATH.read_text(encoding="utf-8"))
    window = MainWindow()
    window.show()
    return app.exec()


if __name__ == "__main__":
    raise SystemExit(main())
