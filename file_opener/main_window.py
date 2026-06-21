from __future__ import annotations

from pathlib import Path

from PySide6.QtGui import QAction, QKeySequence
from PySide6.QtWidgets import (
    QFileDialog,
    QHBoxLayout,
    QLabel,
    QMainWindow,
    QMessageBox,
    QPushButton,
    QTabWidget,
    QVBoxLayout,
    QWidget,
)

from .constants import OPEN_DIALOG_FILTERS
from .document_tab import DocumentTab


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("File Opener")
        self.resize(1280, 900)
        self._build_ui()
        self._build_actions()
        self._build_menu()
        self._connect_controls()
        self.update_controls()

    def _build_ui(self) -> None:
        root = QWidget()
        root_layout = QVBoxLayout(root)
        root_layout.setContentsMargins(8, 8, 8, 8)

        self.tabs = QTabWidget()
        self.tabs.setTabsClosable(True)
        self.tabs.currentChanged.connect(self.update_controls)
        self.tabs.tabCloseRequested.connect(self.close_tab)
        root_layout.addWidget(self.tabs, 1)

        controls = QWidget()
        controls_layout = QHBoxLayout(controls)
        controls_layout.setContentsMargins(0, 0, 0, 0)

        self.btn_prev_file = QPushButton("Файл назад")
        self.btn_next_file = QPushButton("Файл вперед")
        self.btn_rotate_left = QPushButton("Повернуть 90° влево")
        self.btn_rotate_right = QPushButton("Повернуть 90° вправо")
        self.btn_rotate_180 = QPushButton("Повернуть 180°")
        self.btn_flip_h = QPushButton("Отразить по горизонтали")
        self.btn_flip_v = QPushButton("Отразить по вертикали")
        self.btn_zoom_out = QPushButton("Меньше")
        self.btn_zoom_reset = QPushButton("100%")
        self.btn_zoom_in = QPushButton("Крупнее")
        self.btn_reset = QPushButton("Сброс")
        self.btn_prev_page = QPushButton("Предыдущая страница")
        self.btn_next_page = QPushButton("Следующая страница")
        self.status_label = QLabel("Файл не открыт")
        self.status_label.setMinimumWidth(300)

        controls_layout.addWidget(self.btn_prev_file)
        controls_layout.addWidget(self.btn_next_file)
        controls_layout.addWidget(self.btn_rotate_left)
        controls_layout.addWidget(self.btn_rotate_right)
        controls_layout.addWidget(self.btn_rotate_180)
        controls_layout.addWidget(self.btn_flip_h)
        controls_layout.addWidget(self.btn_flip_v)
        controls_layout.addWidget(self.btn_zoom_out)
        controls_layout.addWidget(self.btn_zoom_reset)
        controls_layout.addWidget(self.btn_zoom_in)
        controls_layout.addWidget(self.btn_reset)
        controls_layout.addStretch(1)
        controls_layout.addWidget(self.btn_prev_page)
        controls_layout.addWidget(self.btn_next_page)
        controls_layout.addWidget(self.status_label)

        root_layout.addWidget(controls)
        self.setCentralWidget(root)

    def _build_actions(self) -> None:
        self.open_action = QAction("Открыть файлы...", self)
        self.open_action.setShortcut(QKeySequence.StandardKey.Open)
        self.open_action.triggered.connect(self.open_files)

        self.close_action = QAction("Закрыть текущий файл", self)
        self.close_action.setShortcut(QKeySequence.StandardKey.Close)
        self.close_action.triggered.connect(self.close_current_tab)

        self.exit_action = QAction("Выход", self)
        self.exit_action.setShortcut(QKeySequence("Ctrl+Q"))
        self.exit_action.triggered.connect(self.close)

        self.zoom_in_action = QAction("Увеличить", self)
        self.zoom_in_action.setShortcuts(QKeySequence.StandardKey.ZoomIn)
        self.zoom_in_action.triggered.connect(lambda: self._apply_current("zoom_in"))

        self.zoom_out_action = QAction("Уменьшить", self)
        self.zoom_out_action.setShortcuts(QKeySequence.StandardKey.ZoomOut)
        self.zoom_out_action.triggered.connect(lambda: self._apply_current("zoom_out"))

        self.reset_zoom_action = QAction("Масштаб 100%", self)
        self.reset_zoom_action.setShortcut(QKeySequence("Ctrl+0"))
        self.reset_zoom_action.triggered.connect(lambda: self._apply_current("reset_zoom"))

        self.addActions(
            [
                self.open_action,
                self.close_action,
                self.exit_action,
                self.zoom_in_action,
                self.zoom_out_action,
                self.reset_zoom_action,
            ]
        )

    def _build_menu(self) -> None:
        file_menu = self.menuBar().addMenu("Файл")
        file_menu.addAction(self.open_action)
        file_menu.addAction(self.close_action)
        file_menu.addSeparator()
        file_menu.addAction(self.exit_action)

        view_menu = self.menuBar().addMenu("Вид")
        view_menu.addAction(self.zoom_in_action)
        view_menu.addAction(self.zoom_out_action)
        view_menu.addAction(self.reset_zoom_action)

    def _connect_controls(self) -> None:
        self.btn_prev_file.clicked.connect(lambda: self._apply_current("prev_file"))
        self.btn_next_file.clicked.connect(lambda: self._apply_current("next_file"))
        self.btn_rotate_left.clicked.connect(lambda: self._apply_current("rotate_left"))
        self.btn_rotate_right.clicked.connect(lambda: self._apply_current("rotate_right"))
        self.btn_rotate_180.clicked.connect(lambda: self._apply_current("rotate_180"))
        self.btn_flip_h.clicked.connect(
            lambda: self._apply_current("toggle_flip_horizontal")
        )
        self.btn_flip_v.clicked.connect(lambda: self._apply_current("toggle_flip_vertical"))
        self.btn_zoom_out.clicked.connect(lambda: self._apply_current("zoom_out"))
        self.btn_zoom_reset.clicked.connect(lambda: self._apply_current("reset_zoom"))
        self.btn_zoom_in.clicked.connect(lambda: self._apply_current("zoom_in"))
        self.btn_reset.clicked.connect(lambda: self._apply_current("reset_transform"))
        self.btn_prev_page.clicked.connect(lambda: self._apply_current("prev_page"))
        self.btn_next_page.clicked.connect(lambda: self._apply_current("next_page"))

    def current_tab(self) -> DocumentTab | None:
        widget = self.tabs.currentWidget()
        if isinstance(widget, DocumentTab):
            return widget
        return None

    def open_files(self) -> None:
        files, _ = QFileDialog.getOpenFileNames(
            self, "Открыть файлы", "", OPEN_DIALOG_FILTERS
        )
        if not files:
            return

        for file_path in files:
            existing_index = self._find_opened_tab(file_path)
            if existing_index >= 0:
                self.tabs.setCurrentIndex(existing_index)
                continue

            try:
                tab = DocumentTab(file_path)
            except Exception as exc:
                QMessageBox.warning(
                    self,
                    "Ошибка открытия",
                    f"Файл не удалось открыть:\n{file_path}\n\n{exc}",
                )
                continue

            tab.state_changed.connect(self.update_controls)
            tab.file_changed.connect(
                lambda _path, tab_ref=tab: self._sync_tab_title(tab_ref)
            )
            index = self.tabs.addTab(tab, tab.file_path.name)
            self.tabs.setTabToolTip(index, str(tab.file_path))
            self.tabs.setCurrentIndex(index)

        self.update_controls()

    def _find_opened_tab(self, file_path: str) -> int:
        target = Path(file_path).resolve()
        for idx in range(self.tabs.count()):
            tab = self.tabs.widget(idx)
            if isinstance(tab, DocumentTab) and tab.file_path.resolve() == target:
                return idx
        return -1

    def _sync_tab_title(self, tab: DocumentTab) -> None:
        index = self.tabs.indexOf(tab)
        if index < 0:
            return
        self.tabs.setTabText(index, tab.file_path.name)
        self.tabs.setTabToolTip(index, str(tab.file_path))
        self.update_controls()

    def close_current_tab(self) -> None:
        index = self.tabs.currentIndex()
        if index >= 0:
            self.close_tab(index)

    def close_tab(self, index: int) -> None:
        widget = self.tabs.widget(index)
        if widget is None:
            return
        if isinstance(widget, DocumentTab):
            widget.cleanup()
        self.tabs.removeTab(index)
        widget.deleteLater()
        self.update_controls()

    def _apply_current(self, method_name: str) -> None:
        tab = self.current_tab()
        if tab is None:
            return

        method = getattr(tab, method_name)
        try:
            method()
        except Exception as exc:
            QMessageBox.warning(
                self,
                "Ошибка",
                f"Операция не выполнена для файла:\n{tab.file_path}\n\n{exc}",
            )

        self._sync_tab_title(tab)
        self.update_controls()

    def update_controls(self) -> None:
        tab = self.current_tab()
        enabled = tab is not None
        self.btn_prev_file.setEnabled(enabled and tab.can_prev_file())
        self.btn_next_file.setEnabled(enabled and tab.can_next_file())
        self.btn_rotate_left.setEnabled(enabled)
        self.btn_rotate_right.setEnabled(enabled)
        self.btn_rotate_180.setEnabled(enabled)
        self.btn_flip_h.setEnabled(enabled)
        self.btn_flip_v.setEnabled(enabled)
        self.btn_zoom_out.setEnabled(enabled and tab.can_zoom_out())
        self.btn_zoom_reset.setEnabled(enabled)
        self.btn_zoom_in.setEnabled(enabled and tab.can_zoom_in())
        self.btn_reset.setEnabled(enabled)
        self.zoom_in_action.setEnabled(enabled and tab.can_zoom_in())
        self.zoom_out_action.setEnabled(enabled and tab.can_zoom_out())
        self.reset_zoom_action.setEnabled(enabled)

        if not enabled:
            self.btn_prev_page.setEnabled(False)
            self.btn_next_page.setEnabled(False)
            self.status_label.setText("Файл не открыт")
            self.btn_zoom_reset.setText("100%")
            return

        self.btn_zoom_reset.setText(tab.zoom_text())
        self.btn_prev_page.setEnabled(tab.can_prev_page())
        self.btn_next_page.setEnabled(tab.can_next_page())
        self.status_label.setText(tab.status_text())

    def closeEvent(self, event) -> None:
        for idx in range(self.tabs.count()):
            tab = self.tabs.widget(idx)
            if isinstance(tab, DocumentTab):
                tab.cleanup()
        super().closeEvent(event)
