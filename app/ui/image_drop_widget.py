from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import QPoint, QPointF, QRectF, Qt, Signal
from PySide6.QtGui import QColor, QDragEnterEvent, QDropEvent, QMouseEvent, QPainter, QPen, QPixmap, QWheelEvent
from PySide6.QtWidgets import QWidget


class ImageDropWidget(QWidget):
    image_dropped = Signal(str)
    zoom_changed = Signal(float)

    def __init__(self) -> None:
        super().__init__()
        self.setObjectName("dropArea")
        self.setAcceptDrops(True)

        self._placeholder_text = "Перетащите изображение сюда\nили нажмите 'Открыть изображение'"

        self._source_pixmap: QPixmap | None = None

        self._crop_mode = False
        self._selecting = False
        self._selection_rect = QRectF()
        self._start_point = QPointF()

        self._zoom_factor = 1.0
        self._min_zoom = 0.3
        self._max_zoom = 8.0
        self._pan_offset = QPointF(0.0, 0.0)
        self._panning = False
        self._pan_start = QPoint()
        self._pan_offset_start = QPointF(0.0, 0.0)

        self._image_rect = QRectF()

        self._update_cursor()

    def set_preview_pixmap(self, pixmap: QPixmap | None) -> None:
        self._source_pixmap = pixmap
        self._selection_rect = QRectF()
        self._zoom_factor = 1.0
        self._pan_offset = QPointF(0.0, 0.0)
        self._update_image_rect()
        self.zoom_changed.emit(self._zoom_factor)
        self.update()

    def set_crop_mode(self, enabled: bool) -> None:
        self._crop_mode = enabled
        self._selecting = False
        self._update_cursor()
        self.update()

    def clear_selection(self) -> None:
        self._selection_rect = QRectF()
        self._selecting = False
        self.update()

    def zoom_in(self) -> None:
        self._set_zoom(self._zoom_factor * 1.2, anchor=self.rect().center())

    def zoom_out(self) -> None:
        self._set_zoom(self._zoom_factor / 1.2, anchor=self.rect().center())

    def reset_view(self) -> None:
        self._zoom_factor = 1.0
        self._pan_offset = QPointF(0.0, 0.0)
        self._update_image_rect()
        self.zoom_changed.emit(self._zoom_factor)
        self.update()

    def get_zoom_factor(self) -> float:
        return self._zoom_factor

    def get_crop_rect(self, image_width: int, image_height: int) -> tuple[int, int, int, int] | None:
        if self._image_rect.isNull() or self._selection_rect.isNull():
            return None

        selection = self._selection_rect.intersected(self._image_rect)
        if selection.isNull() or selection.width() < 3 or selection.height() < 3:
            return None

        x_ratio = image_width / self._image_rect.width()
        y_ratio = image_height / self._image_rect.height()

        x = int((selection.x() - self._image_rect.x()) * x_ratio)
        y = int((selection.y() - self._image_rect.y()) * y_ratio)
        w = int(selection.width() * x_ratio)
        h = int(selection.height() * y_ratio)

        x = max(0, min(x, image_width - 1))
        y = max(0, min(y, image_height - 1))
        w = max(1, min(w, image_width - x))
        h = max(1, min(h, image_height - y))

        return (x, y, w, h)

    def dragEnterEvent(self, event: QDragEnterEvent) -> None:  # noqa: N802
        if self._has_image_url(event):
            event.acceptProposedAction()
        else:
            event.ignore()

    def dropEvent(self, event: QDropEvent) -> None:  # noqa: N802
        mime_data = event.mimeData()
        if not mime_data.hasUrls():
            event.ignore()
            return

        for url in mime_data.urls():
            if not url.isLocalFile():
                continue

            path = Path(url.toLocalFile())
            if path.suffix.lower() in {".png", ".jpg", ".jpeg", ".bmp", ".tif", ".tiff"}:
                self.image_dropped.emit(str(path))
                event.acceptProposedAction()
                return

        event.ignore()

    def wheelEvent(self, event: QWheelEvent) -> None:
        if self._source_pixmap is None:
            return

        delta = event.angleDelta().y()
        if delta > 0:
            self._set_zoom(self._zoom_factor * 1.15, anchor=event.position())
        elif delta < 0:
            self._set_zoom(self._zoom_factor / 1.15, anchor=event.position())

    def mousePressEvent(self, event: QMouseEvent) -> None:
        if self._source_pixmap is None:
            return

        if self._crop_mode and event.button() == Qt.LeftButton and self._image_rect.contains(event.position()):
            self._selecting = True
            self._start_point = self._clamp_point_to_image(event.position())
            self._selection_rect = QRectF(self._start_point, self._start_point)
            self.update()
            return

        if event.button() == Qt.MiddleButton or (event.button() == Qt.LeftButton and not self._crop_mode):
            self._panning = True
            self._pan_start = event.position().toPoint()
            self._pan_offset_start = QPointF(self._pan_offset)
            self._update_cursor(force_closed_hand=True)
            return

    def mouseMoveEvent(self, event: QMouseEvent) -> None:
        if self._selecting:
            current = self._clamp_point_to_image(event.position())
            self._selection_rect = QRectF(self._start_point, current).normalized()
            self.update()
            return

        if self._panning:
            delta = event.position().toPoint() - self._pan_start
            self._pan_offset = QPointF(
                self._pan_offset_start.x() + delta.x(),
                self._pan_offset_start.y() + delta.y(),
            )
            self._update_image_rect()
            self.update()
            return

    def mouseReleaseEvent(self, event: QMouseEvent) -> None:
        if self._selecting and event.button() == Qt.LeftButton:
            self._selecting = False
            if self._selection_rect.width() < 3 or self._selection_rect.height() < 3:
                self._selection_rect = QRectF()
            self.update()
            return

        if self._panning and (event.button() == Qt.MiddleButton or event.button() == Qt.LeftButton):
            self._panning = False
            self._update_cursor()
            return

    def resizeEvent(self, event) -> None:  # noqa: N802
        super().resizeEvent(event)
        self._update_image_rect()
        self.update()

    def paintEvent(self, event) -> None:  # noqa: N802
        super().paintEvent(event)

        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)

        if self._source_pixmap is None or self._source_pixmap.isNull():
            painter.setPen(QColor(60, 78, 99))
            painter.drawText(self.rect(), Qt.AlignCenter, self._placeholder_text)
            return

        painter.drawPixmap(self._image_rect, self._source_pixmap, QRectF(self._source_pixmap.rect()))

        if self._crop_mode:
            if not self._selection_rect.isNull():
                painter.fillRect(self._selection_rect, QColor(30, 80, 160, 45))
                painter.setPen(QPen(QColor(37, 93, 173), 2, Qt.DashLine))
                painter.drawRect(self._selection_rect)
            else:
                painter.setPen(QPen(QColor(124, 151, 186), 1, Qt.DotLine))
                painter.drawRect(self._image_rect)

    def _set_zoom(self, value: float, anchor: QPointF) -> None:
        if self._source_pixmap is None:
            return

        new_zoom = max(self._min_zoom, min(value, self._max_zoom))
        if abs(new_zoom - self._zoom_factor) < 1e-4:
            return

        old_rect = QRectF(self._image_rect)
        if old_rect.isNull():
            self._zoom_factor = new_zoom
            self._update_image_rect()
            self.zoom_changed.emit(self._zoom_factor)
            self.update()
            return

        u = (anchor.x() - old_rect.x()) / old_rect.width()
        v = (anchor.y() - old_rect.y()) / old_rect.height()

        self._zoom_factor = new_zoom

        base_scale = self._base_scale()
        new_scale = base_scale * self._zoom_factor
        new_w = self._source_pixmap.width() * new_scale
        new_h = self._source_pixmap.height() * new_scale

        center_x = (self.width() - new_w) / 2.0
        center_y = (self.height() - new_h) / 2.0

        self._pan_offset = QPointF(
            anchor.x() - (u * new_w) - center_x,
            anchor.y() - (v * new_h) - center_y,
        )

        self._update_image_rect()
        self.zoom_changed.emit(self._zoom_factor)
        self.update()

    def _update_image_rect(self) -> None:
        if self._source_pixmap is None or self._source_pixmap.isNull():
            self._image_rect = QRectF()
            return

        base_scale = self._base_scale()
        scale = base_scale * self._zoom_factor

        w = self._source_pixmap.width() * scale
        h = self._source_pixmap.height() * scale

        self._clamp_pan(w, h)

        x = (self.width() - w) / 2.0 + self._pan_offset.x()
        y = (self.height() - h) / 2.0 + self._pan_offset.y()

        self._image_rect = QRectF(x, y, w, h)

        if not self._selection_rect.isNull():
            self._selection_rect = self._selection_rect.intersected(self._image_rect)
            if self._selection_rect.width() < 3 or self._selection_rect.height() < 3:
                self._selection_rect = QRectF()

    def _clamp_pan(self, image_w: float, image_h: float) -> None:
        if image_w <= self.width():
            pan_x = 0.0
        else:
            max_x = (image_w - self.width()) / 2.0
            pan_x = max(-max_x, min(self._pan_offset.x(), max_x))

        if image_h <= self.height():
            pan_y = 0.0
        else:
            max_y = (image_h - self.height()) / 2.0
            pan_y = max(-max_y, min(self._pan_offset.y(), max_y))

        self._pan_offset = QPointF(pan_x, pan_y)

    def _base_scale(self) -> float:
        if self._source_pixmap is None or self._source_pixmap.isNull() or self.width() <= 0 or self.height() <= 0:
            return 1.0

        return min(
            self.width() / self._source_pixmap.width(),
            self.height() / self._source_pixmap.height(),
        )

    def _clamp_point_to_image(self, point: QPointF) -> QPointF:
        x = min(max(point.x(), self._image_rect.left()), self._image_rect.right())
        y = min(max(point.y(), self._image_rect.top()), self._image_rect.bottom())
        return QPointF(x, y)

    def _update_cursor(self, force_closed_hand: bool = False) -> None:
        if force_closed_hand:
            self.setCursor(Qt.ClosedHandCursor)
            return

        if self._crop_mode:
            self.setCursor(Qt.CrossCursor)
        else:
            self.setCursor(Qt.OpenHandCursor)

    @staticmethod
    def _has_image_url(event: QDragEnterEvent) -> bool:
        mime_data = event.mimeData()
        if not mime_data.hasUrls():
            return False

        for url in mime_data.urls():
            if url.isLocalFile() and Path(url.toLocalFile()).suffix.lower() in {
                ".png",
                ".jpg",
                ".jpeg",
                ".bmp",
                ".tif",
                ".tiff",
            }:
                return True
        return False
