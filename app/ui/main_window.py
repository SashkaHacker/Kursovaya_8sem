from __future__ import annotations

from datetime import datetime

import cv2
from PySide6.QtCore import Qt
from PySide6.QtGui import QPixmap, QTransform
from PySide6.QtWidgets import (
    QAbstractItemView,
    QFileDialog,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QMainWindow,
    QMessageBox,
    QPushButton,
    QTableWidget,
    QTableWidgetItem,
    QTextEdit,
    QToolButton,
    QVBoxLayout,
    QWidget,
)

from app.config import APP_TITLE, DB_PATH, UPLOADS_DIR
from app.database.db_service import DatabaseService
from app.models.history_entry import HistoryEntry
from app.services.image_preprocessing_service import ImagePreprocessingService
from app.services.ocr_service import OCRService
from app.ui.image_drop_widget import ImageDropWidget


class MainWindow(QMainWindow):
    def __init__(self) -> None:
        super().__init__()

        self.setWindowTitle(APP_TITLE)
        self.resize(1260, 820)

        self.preprocessing_service = ImagePreprocessingService()
        self.ocr_service = OCRService()
        self.db_service = DatabaseService(DB_PATH)

        self.current_image_path: str = ""
        self.original_pixmap: QPixmap | None = None
        self.rotation_angle: int = 0

        self.history_entries: list[HistoryEntry] = []

        self._build_ui()
        self._load_history()

    def _build_ui(self) -> None:
        central = QWidget()
        self.setCentralWidget(central)

        self.open_button = QPushButton("Открыть изображение")
        self.open_button.clicked.connect(self._open_image_dialog)

        self.recognize_button = QPushButton("Распознать")
        self.recognize_button.clicked.connect(self._recognize_text)

        controls = QHBoxLayout()
        controls.addWidget(self.open_button)
        controls.addWidget(self.recognize_button)
        controls.addStretch(1)

        self.drop_area = ImageDropWidget()
        self.drop_area.setMinimumHeight(600)
        self.drop_area.image_dropped.connect(self._set_image)
        self.drop_area.zoom_changed.connect(self._on_zoom_changed)

        self.view_info_label = QLabel("∠ 0° | 100%")
        self.view_info_label.setObjectName("rotationLabel")
        self.view_info_label.setAlignment(Qt.AlignVCenter | Qt.AlignRight)

        self.rotate_left_button = self._make_image_tool_button("↺", "Повернуть влево", lambda: self._rotate(-90))
        self.rotate_right_button = self._make_image_tool_button("↻", "Повернуть вправо", lambda: self._rotate(90))
        self.zoom_in_button = self._make_image_tool_button("＋", "Увеличить", self._zoom_in)
        self.zoom_out_button = self._make_image_tool_button("－", "Уменьшить", self._zoom_out)
        self.zoom_reset_button = self._make_image_tool_button("⌂", "Сбросить масштаб и позицию", self._reset_view)
        self.crop_mode_button = self._make_image_tool_button(
            "✂",
            "Режим обрезки",
            None,
            checkable=True,
        )
        self.crop_mode_button.toggled.connect(self._toggle_crop_mode)
        self.clear_crop_button = self._make_image_tool_button("⌫", "Сбросить выделение", self._clear_crop)

        image_tools = QHBoxLayout()
        image_tools.addWidget(self.rotate_left_button)
        image_tools.addWidget(self.rotate_right_button)
        image_tools.addSpacing(6)
        image_tools.addWidget(self.zoom_in_button)
        image_tools.addWidget(self.zoom_out_button)
        image_tools.addWidget(self.zoom_reset_button)
        image_tools.addSpacing(6)
        image_tools.addWidget(self.crop_mode_button)
        image_tools.addWidget(self.clear_crop_button)
        image_tools.addStretch(1)
        image_tools.addWidget(self.view_info_label)

        left_side = QVBoxLayout()
        left_side.addLayout(controls)
        left_side.addWidget(self.drop_area, 1)
        left_side.addLayout(image_tools)

        self.text_output = QTextEdit()
        self.text_output.setPlaceholderText("Распознанный текст (можно редактировать перед сохранением)")

        self.save_history_button = QPushButton("Сохранить в историю")
        self.save_history_button.clicked.connect(self._save_text_to_history)

        text_header = QHBoxLayout()
        text_header.addWidget(QLabel("Текст (редактируемый):"))
        text_header.addStretch(1)
        text_header.addWidget(self.save_history_button)

        self.history_table = QTableWidget(0, 3)
        self.history_table.setHorizontalHeaderLabels(["Дата", "Время", "Текст"])
        self.history_table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.history_table.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.history_table.setSelectionMode(QAbstractItemView.SingleSelection)
        self.history_table.itemSelectionChanged.connect(self._open_selected_history_entry)

        header = self.history_table.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.ResizeToContents)
        header.setSectionResizeMode(1, QHeaderView.ResizeToContents)
        header.setSectionResizeMode(2, QHeaderView.Stretch)

        right_side = QVBoxLayout()
        right_side.addLayout(text_header)
        right_side.addWidget(self.text_output, 4)
        right_side.addWidget(QLabel("История распознаваний:"))
        right_side.addWidget(self.history_table, 5)

        content = QHBoxLayout(central)
        content.addLayout(left_side, 60)
        content.addLayout(right_side, 40)

        self.statusBar().showMessage("Готово")

    def _make_image_tool_button(
        self,
        glyph: str,
        tooltip: str,
        handler,
        checkable: bool = False,
    ) -> QToolButton:
        button = QToolButton()
        button.setText(glyph)
        button.setToolTip(tooltip)
        button.setCheckable(checkable)
        button.setAutoRaise(False)
        button.setObjectName("imageToolButton")
        button.setFixedSize(38, 38)
        if handler is not None:
            button.clicked.connect(handler)
        return button

    def _open_image_dialog(self) -> None:
        image_path, _ = QFileDialog.getOpenFileName(
            self,
            "Выберите изображение",
            str(UPLOADS_DIR),
            "Images (*.png *.jpg *.jpeg *.bmp *.tif *.tiff)",
        )
        if image_path:
            self._set_image(image_path)

    def _set_image(self, image_path: str) -> None:
        pixmap = QPixmap(image_path)
        if pixmap.isNull():
            QMessageBox.critical(self, "Ошибка", "Не удалось открыть изображение")
            return

        self.current_image_path = image_path
        self.original_pixmap = pixmap
        self.rotation_angle = 0
        self.drop_area.clear_selection()
        self._render_image()
        self._update_view_info()

        self.statusBar().showMessage(f"Загружено изображение: {image_path}")

    def _rotate(self, delta_angle: int) -> None:
        if self.original_pixmap is None:
            QMessageBox.warning(self, "Нет изображения", "Сначала загрузите изображение")
            return

        self.rotation_angle = (self.rotation_angle + delta_angle) % 360
        self.drop_area.clear_selection()
        self._render_image()
        self._update_view_info()

    def _zoom_in(self) -> None:
        self.drop_area.zoom_in()

    def _zoom_out(self) -> None:
        self.drop_area.zoom_out()

    def _reset_view(self) -> None:
        self.drop_area.reset_view()

    def _on_zoom_changed(self, _zoom: float) -> None:
        self._update_view_info()

    def _update_view_info(self) -> None:
        zoom_percent = int(round(self.drop_area.get_zoom_factor() * 100))
        self.view_info_label.setText(f"∠ {self.rotation_angle}° | {zoom_percent}%")

    def _toggle_crop_mode(self, enabled: bool) -> None:
        self.drop_area.set_crop_mode(enabled)
        if enabled:
            self.statusBar().showMessage("Режим обрезки включен: выделите область на изображении")
        else:
            self.statusBar().showMessage("Режим обрезки выключен")

    def _clear_crop(self) -> None:
        self.drop_area.clear_selection()
        self.statusBar().showMessage("Выделение области сброшено")

    def _render_image(self) -> None:
        if self.original_pixmap is None:
            self.drop_area.set_preview_pixmap(None)
            return

        transformed = self.original_pixmap.transformed(QTransform().rotate(self.rotation_angle), Qt.SmoothTransformation)
        self.drop_area.set_preview_pixmap(transformed)

    def resizeEvent(self, event) -> None:  # noqa: N802
        super().resizeEvent(event)

    def _get_rotated_cv_image(self):
        image = self.preprocessing_service.load_image(self.current_image_path)

        if self.rotation_angle == 90:
            return cv2.rotate(image, cv2.ROTATE_90_CLOCKWISE)
        if self.rotation_angle == 180:
            return cv2.rotate(image, cv2.ROTATE_180)
        if self.rotation_angle == 270:
            return cv2.rotate(image, cv2.ROTATE_90_COUNTERCLOCKWISE)
        return image

    def _recognize_text(self) -> None:
        if not self.current_image_path:
            QMessageBox.warning(self, "Нет изображения", "Сначала загрузите изображение")
            return

        try:
            image = self._get_rotated_cv_image()

            crop_rect = None
            if self.crop_mode_button.isChecked():
                crop_rect = self.drop_area.get_crop_rect(image.shape[1], image.shape[0])
            if crop_rect is not None:
                x, y, w, h = crop_rect
                image = image[y : y + h, x : x + w]

            prepared_image = self.preprocessing_service.preprocess_for_ocr(image)
            recognized_text = self.ocr_service.extract_text(prepared_image)

            if not recognized_text:
                QMessageBox.warning(self, "OCR", "OCR не вернул текст")
                return

            self.text_output.setPlainText(recognized_text)
            self.statusBar().showMessage(
                "Распознавание выполнено. При необходимости отредактируйте текст и нажмите 'Сохранить в историю'"
            )

        except RuntimeError as exc:
            QMessageBox.critical(self, "Ошибка OCR", str(exc))
        except Exception as exc:
            QMessageBox.critical(self, "Ошибка", f"Не удалось распознать текст: {exc}")

    def _save_text_to_history(self) -> None:
        text = self.text_output.toPlainText().strip()
        if not text:
            QMessageBox.warning(self, "Нет текста", "Нет текста для сохранения")
            return

        try:
            created_at = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            self.db_service.add_entry(created_at=created_at, recognized_text=text)
            self._load_history()
            if self.history_entries:
                self.history_table.selectRow(0)

            self.statusBar().showMessage("Текст сохранен в историю")
        except Exception as exc:
            QMessageBox.critical(self, "Ошибка БД", f"Не удалось сохранить запись: {exc}")

    def _load_history(self) -> None:
        try:
            self.history_entries = self.db_service.list_entries()
        except Exception as exc:
            QMessageBox.critical(self, "Ошибка БД", f"Не удалось загрузить историю: {exc}")
            return

        self.history_table.setRowCount(len(self.history_entries))

        for index, entry in enumerate(self.history_entries):
            self._set_history_row(index, entry)

    def _set_history_row(self, row: int, entry: HistoryEntry) -> None:
        preview_text = entry.recognized_text.replace("\n", " ")
        if len(preview_text) > 120:
            preview_text = f"{preview_text[:117]}..."

        date_item = QTableWidgetItem(entry.date_str)
        time_item = QTableWidgetItem(entry.time_str)
        text_item = QTableWidgetItem(preview_text)

        self.history_table.setItem(row, 0, date_item)
        self.history_table.setItem(row, 1, time_item)
        self.history_table.setItem(row, 2, text_item)

    def _open_selected_history_entry(self) -> None:
        selected_items = self.history_table.selectedItems()
        if not selected_items:
            return

        row = selected_items[0].row()
        if row < 0 or row >= len(self.history_entries):
            return

        entry = self.history_entries[row]
        self.text_output.setPlainText(entry.recognized_text)
        self.statusBar().showMessage(f"Открыта запись из истории: {entry.date_str} {entry.time_str}")
