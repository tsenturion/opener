from __future__ import annotations

from pathlib import Path

import fitz
from PySide6.QtCore import QEvent, QPointF, Qt, Signal
from PySide6.QtGui import QImage, QPixmap, QTransform
from PySide6.QtWidgets import QLabel, QScrollArea, QVBoxLayout, QWidget

from .constants import (
    DEFAULT_ZOOM,
    MAX_ZOOM,
    MIN_ZOOM,
    PDF_RENDER_SCALE,
    SUPPORTED_EXTENSIONS,
    ZOOM_STEP,
)


class DocumentTab(QWidget):
    state_changed = Signal()
    file_changed = Signal(str)

    def __init__(self, file_path: str):
        super().__init__()
        self.file_path = Path(file_path)
        self.is_pdf = False
        self.rotation_deg = 0
        self.flip_horizontal = False
        self.flip_vertical = False
        self.zoom_factor = DEFAULT_ZOOM
        self.current_page = 0
        self.page_count = 1
        self.directory_files: list[Path] = []
        self.directory_index = -1
        self._pdf_doc: fitz.Document | None = None
        self._image: QImage | None = None

        self._build_ui()
        self.open_file(self.file_path, reset_transform=True)

    def _build_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)

        self.scroll_area = QScrollArea()
        self.scroll_area.setWidgetResizable(False)
        self.scroll_area.setAlignment(Qt.AlignCenter)

        self.preview_label = QLabel()
        self.preview_label.setAlignment(Qt.AlignCenter)
        self.preview_label.setText("Загрузка файла...")

        self.preview_label.installEventFilter(self)
        self.scroll_area.viewport().installEventFilter(self)
        self.scroll_area.setWidget(self.preview_label)
        layout.addWidget(self.scroll_area)

    def eventFilter(self, watched, event) -> bool:
        if event.type() != QEvent.Type.Wheel:
            return super().eventFilter(watched, event)

        if not event.modifiers() & Qt.KeyboardModifier.ControlModifier:
            return super().eventFilter(watched, event)

        wheel_delta = event.angleDelta().y()
        if wheel_delta == 0:
            wheel_delta = event.pixelDelta().y()
        if wheel_delta == 0:
            return True

        viewport_anchor, content_anchor = self._zoom_anchors(watched, event)
        steps = (
            wheel_delta / 120
            if event.angleDelta().y()
            else (1 if wheel_delta > 0 else -1)
        )
        self.zoom_by_steps(steps, viewport_anchor, content_anchor)
        event.accept()
        return True

    def _zoom_anchors(self, watched, event) -> tuple[QPointF, QPointF | None]:
        event_pos = event.position()
        if watched is self.preview_label:
            viewport_pos = self.preview_label.mapTo(
                self.scroll_area.viewport(), event_pos.toPoint()
            )
            return QPointF(viewport_pos), event_pos

        return event_pos, None

    def _reset_transform_state(self) -> None:
        self.rotation_deg = 0
        self.flip_horizontal = False
        self.flip_vertical = False
        self.zoom_factor = DEFAULT_ZOOM

    def _close_loaded_document(self) -> None:
        if self._pdf_doc is not None:
            self._pdf_doc.close()
            self._pdf_doc = None
        self._image = None

    def _refresh_directory_listing(self) -> None:
        try:
            files = [
                item
                for item in self.file_path.parent.iterdir()
                if item.is_file() and item.suffix.lower() in SUPPORTED_EXTENSIONS
            ]
            files.sort(key=lambda item: item.name.casefold())
        except OSError:
            files = [self.file_path]

        self.directory_files = files
        resolved_current = self.file_path.resolve()
        self.directory_index = next(
            (
                idx
                for idx, item in enumerate(self.directory_files)
                if item.resolve() == resolved_current
            ),
            -1,
        )

        if self.directory_index == -1:
            self.directory_files.append(self.file_path)
            self.directory_files.sort(key=lambda item: item.name.casefold())
            self.directory_index = next(
                idx
                for idx, item in enumerate(self.directory_files)
                if item.resolve() == resolved_current
            )

    def open_file(self, file_path: str | Path, reset_transform: bool = True) -> None:
        target = Path(file_path)
        if not target.exists() or not target.is_file():
            raise FileNotFoundError(f"Файл не найден: {target}")
        if target.suffix.lower() not in SUPPORTED_EXTENSIONS:
            raise ValueError(f"Неподдерживаемый формат: {target.suffix}")

        next_is_pdf = target.suffix.lower() == ".pdf"
        next_pdf_doc = None
        next_image = None
        next_page_count = 1

        if next_is_pdf:
            next_pdf_doc = fitz.open(target)
            next_page_count = next_pdf_doc.page_count
        else:
            image = QImage(str(target))
            if image.isNull():
                raise ValueError("Не удалось открыть изображение.")
            next_image = image

        self._close_loaded_document()
        self.file_path = target
        self.is_pdf = next_is_pdf
        self.current_page = 0
        self.page_count = next_page_count
        self._pdf_doc = next_pdf_doc
        self._image = next_image

        if reset_transform:
            self._reset_transform_state()

        self._refresh_directory_listing()
        self.render()
        self.file_changed.emit(str(self.file_path))

    def _pixmap_from_pdf_page(self) -> QPixmap:
        if self._pdf_doc is None:
            raise RuntimeError("PDF не загружен.")

        page = self._pdf_doc.load_page(self.current_page)
        matrix = fitz.Matrix(PDF_RENDER_SCALE, PDF_RENDER_SCALE)
        rendered = page.get_pixmap(matrix=matrix, alpha=True)
        image = self._qimage_from_fitz(rendered)
        return QPixmap.fromImage(image)

    @staticmethod
    def _qimage_from_fitz(pixmap: fitz.Pixmap) -> QImage:
        if pixmap.n == 1:
            fmt = QImage.Format_Grayscale8
            image = QImage(
                pixmap.samples, pixmap.width, pixmap.height, pixmap.stride, fmt
            )
            return image.copy()
        if pixmap.n == 3:
            fmt = QImage.Format_RGB888
            image = QImage(
                pixmap.samples, pixmap.width, pixmap.height, pixmap.stride, fmt
            )
            return image.copy()
        if pixmap.n == 4:
            fmt = QImage.Format_RGBA8888
            image = QImage(
                pixmap.samples, pixmap.width, pixmap.height, pixmap.stride, fmt
            )
            return image.copy()

        converted = fitz.Pixmap(fitz.csRGB, pixmap)
        image = QImage(
            converted.samples,
            converted.width,
            converted.height,
            converted.stride,
            QImage.Format_RGB888,
        )
        return image.copy()

    def _source_pixmap(self) -> QPixmap:
        if self.is_pdf:
            return self._pixmap_from_pdf_page()
        if self._image is None:
            raise RuntimeError("Изображение не загружено.")
        return QPixmap.fromImage(self._image)

    def _apply_transform(self, pixmap: QPixmap) -> QPixmap:
        transform = QTransform()
        sx = self.zoom_factor * (-1 if self.flip_horizontal else 1)
        sy = self.zoom_factor * (-1 if self.flip_vertical else 1)
        transform.scale(sx, sy)
        if self.rotation_deg:
            transform.rotate(self.rotation_deg)
        return pixmap.transformed(transform, Qt.SmoothTransformation)

    def render(self) -> None:
        base = self._source_pixmap()
        final = self._apply_transform(base)
        self.preview_label.setPixmap(final)
        self.preview_label.adjustSize()
        self.state_changed.emit()

    def rotate_left(self) -> None:
        self.rotation_deg = (self.rotation_deg - 90) % 360
        self.render()

    def rotate_right(self) -> None:
        self.rotation_deg = (self.rotation_deg + 90) % 360
        self.render()

    def rotate_180(self) -> None:
        self.rotation_deg = (self.rotation_deg + 180) % 360
        self.render()

    def toggle_flip_horizontal(self) -> None:
        self.flip_horizontal = not self.flip_horizontal
        self.render()

    def toggle_flip_vertical(self) -> None:
        self.flip_vertical = not self.flip_vertical
        self.render()

    def reset_transform(self) -> None:
        self._reset_transform_state()
        self.render()

    def can_zoom_in(self) -> bool:
        return self.zoom_factor < MAX_ZOOM

    def can_zoom_out(self) -> bool:
        return self.zoom_factor > MIN_ZOOM

    def zoom_in(self) -> None:
        self.zoom_by_steps(1)

    def zoom_out(self) -> None:
        self.zoom_by_steps(-1)

    def reset_zoom(self) -> None:
        self.set_zoom(DEFAULT_ZOOM)

    def zoom_by_steps(
        self,
        steps: float,
        viewport_anchor: QPointF | None = None,
        content_anchor: QPointF | None = None,
    ) -> None:
        self.set_zoom(
            self.zoom_factor * (ZOOM_STEP**steps), viewport_anchor, content_anchor
        )

    def set_zoom(
        self,
        zoom_factor: float,
        viewport_anchor: QPointF | None = None,
        content_anchor: QPointF | None = None,
    ) -> None:
        next_zoom = max(MIN_ZOOM, min(MAX_ZOOM, zoom_factor))
        if abs(next_zoom - self.zoom_factor) < 0.001:
            return

        if viewport_anchor is None:
            viewport = self.scroll_area.viewport()
            viewport_anchor = QPointF(viewport.width() / 2, viewport.height() / 2)

        hbar = self.scroll_area.horizontalScrollBar()
        vbar = self.scroll_area.verticalScrollBar()
        if content_anchor is None:
            content_anchor = QPointF(
                hbar.value() + viewport_anchor.x(),
                vbar.value() + viewport_anchor.y(),
            )

        old_width = max(1, self.preview_label.width())
        old_height = max(1, self.preview_label.height())
        content_ratio_x = content_anchor.x() / old_width
        content_ratio_y = content_anchor.y() / old_height

        self.zoom_factor = next_zoom
        self.render()

        hbar.setValue(
            round(self.preview_label.width() * content_ratio_x - viewport_anchor.x())
        )
        vbar.setValue(
            round(self.preview_label.height() * content_ratio_y - viewport_anchor.y())
        )

    def can_prev_page(self) -> bool:
        return self.is_pdf and self.current_page > 0

    def can_next_page(self) -> bool:
        return self.is_pdf and self.current_page < (self.page_count - 1)

    def prev_page(self) -> None:
        if self.can_prev_page():
            self.current_page -= 1
            self.render()

    def next_page(self) -> None:
        if self.can_next_page():
            self.current_page += 1
            self.render()

    def can_prev_file(self) -> bool:
        return self.directory_index > 0

    def can_next_file(self) -> bool:
        return self.directory_index >= 0 and self.directory_index < (
            len(self.directory_files) - 1
        )

    def prev_file(self) -> None:
        if self.can_prev_file():
            self.open_file(self.directory_files[self.directory_index - 1], True)

    def next_file(self) -> None:
        if self.can_next_file():
            self.open_file(self.directory_files[self.directory_index + 1], True)

    def page_text(self) -> str:
        if self.is_pdf:
            return f"Страница {self.current_page + 1}/{self.page_count}"
        return "Изображение"

    def zoom_text(self) -> str:
        return f"{round(self.zoom_factor * 100)}%"

    def status_text(self) -> str:
        if self.directory_index >= 0 and self.directory_files:
            file_pos = f"Файл {self.directory_index + 1}/{len(self.directory_files)}"
        else:
            file_pos = self.file_path.name
        return f"{file_pos} | {self.page_text()} | Масштаб {self.zoom_text()}"

    def cleanup(self) -> None:
        self._close_loaded_document()
