from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import Qt
from PySide6.QtGui import QAction, QActionGroup, QGuiApplication, QKeySequence
from PySide6.QtWidgets import (
    QFileDialog,
    QLabel,
    QMainWindow,
    QMessageBox,
    QSizePolicy,
    QTabWidget,
    QToolBar,
)

from .constants import OPEN_DIALOG_FILTERS
from .document_tab import (
    SORT_FIELD_LABELS,
    DirectorySort,
    DocumentTab,
    SortField,
    sorted_supported_files,
)


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("File Opener")
        self.directory_sort = DirectorySort()
        self._resize_to_available_screen()
        self._build_ui()
        self._build_actions()
        self._build_menu()
        self._build_toolbar()
        self.update_controls()

    def _resize_to_available_screen(self) -> None:
        target_width = 1280
        target_height = 900
        screen = self.screen() or QGuiApplication.primaryScreen()
        if screen is None:
            self.resize(target_width, target_height)
            return

        available = screen.availableGeometry()
        width = max(1, min(target_width, int(available.width() * 0.95)))
        height = max(1, min(target_height, int(available.height() * 0.95)))
        self.resize(width, height)

    def _build_ui(self) -> None:
        self.tabs = QTabWidget()
        self.tabs.setTabsClosable(True)
        self.tabs.currentChanged.connect(self.update_controls)
        self.tabs.tabCloseRequested.connect(self.close_tab)
        self.setCentralWidget(self.tabs)

        self.status_label = QLabel("Файл не открыт")
        self.status_label.setMinimumWidth(300)
        self.status_label.setSizePolicy(
            QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred
        )

    def _build_actions(self) -> None:
        self.open_action = QAction("Открыть файлы...", self)
        self.open_action.setIconText("Файлы")
        self.open_action.setShortcut(QKeySequence.StandardKey.Open)
        self.open_action.triggered.connect(self.open_files)

        self.open_folder_action = QAction("Открыть папку...", self)
        self.open_folder_action.setIconText("Папка")
        self.open_folder_action.setShortcut(QKeySequence("Ctrl+Shift+O"))
        self.open_folder_action.triggered.connect(self.open_folder)

        self.close_action = QAction("Закрыть текущий файл", self)
        self.close_action.setShortcut(QKeySequence.StandardKey.Close)
        self.close_action.triggered.connect(self.close_current_tab)

        self.exit_action = QAction("Выход", self)
        self.exit_action.setShortcut(QKeySequence("Ctrl+Q"))
        self.exit_action.triggered.connect(self.close)

        self.prev_file_action = QAction("Предыдущий файл", self)
        self.prev_file_action.setIconText("← Файл")
        self.prev_file_action.setShortcut(QKeySequence("Alt+Left"))
        self.prev_file_action.triggered.connect(lambda: self._apply_current("prev_file"))

        self.next_file_action = QAction("Следующий файл", self)
        self.next_file_action.setIconText("Файл →")
        self.next_file_action.setShortcut(QKeySequence("Alt+Right"))
        self.next_file_action.triggered.connect(lambda: self._apply_current("next_file"))

        self.prev_page_action = QAction("Предыдущая страница", self)
        self.prev_page_action.setIconText("← Стр.")
        self.prev_page_action.setShortcut(QKeySequence("PageUp"))
        self.prev_page_action.triggered.connect(lambda: self._apply_current("prev_page"))

        self.next_page_action = QAction("Следующая страница", self)
        self.next_page_action.setIconText("Стр. →")
        self.next_page_action.setShortcut(QKeySequence("PageDown"))
        self.next_page_action.triggered.connect(lambda: self._apply_current("next_page"))

        self.rotate_left_action = QAction("Повернуть 90° влево", self)
        self.rotate_left_action.setIconText("↶ 90°")
        self.rotate_left_action.setShortcut(QKeySequence("Ctrl+["))
        self.rotate_left_action.triggered.connect(
            lambda: self._apply_current("rotate_left")
        )

        self.rotate_right_action = QAction("Повернуть 90° вправо", self)
        self.rotate_right_action.setIconText("90° ↷")
        self.rotate_right_action.setShortcut(QKeySequence("Ctrl+]"))
        self.rotate_right_action.triggered.connect(
            lambda: self._apply_current("rotate_right")
        )

        self.rotate_180_action = QAction("Повернуть 180°", self)
        self.rotate_180_action.triggered.connect(lambda: self._apply_current("rotate_180"))

        self.flip_horizontal_action = QAction("Отразить по горизонтали", self)
        self.flip_horizontal_action.triggered.connect(
            lambda: self._apply_current("toggle_flip_horizontal")
        )

        self.flip_vertical_action = QAction("Отразить по вертикали", self)
        self.flip_vertical_action.triggered.connect(
            lambda: self._apply_current("toggle_flip_vertical")
        )

        self.reset_transform_action = QAction("Сбросить поворот и отражение", self)
        self.reset_transform_action.triggered.connect(
            lambda: self._apply_current("reset_transform")
        )

        self.zoom_in_action = QAction("Увеличить", self)
        self.zoom_in_action.setShortcuts(QKeySequence.StandardKey.ZoomIn)
        self.zoom_in_action.triggered.connect(lambda: self._apply_current("zoom_in"))

        self.zoom_out_action = QAction("Уменьшить", self)
        self.zoom_out_action.setShortcuts(QKeySequence.StandardKey.ZoomOut)
        self.zoom_out_action.triggered.connect(lambda: self._apply_current("zoom_out"))

        self.reset_zoom_action = QAction("Масштаб 100%", self)
        self.reset_zoom_action.setShortcut(QKeySequence("Ctrl+0"))
        self.reset_zoom_action.triggered.connect(lambda: self._apply_current("reset_zoom"))

        self.sort_field_group = QActionGroup(self)
        self.sort_field_actions: dict[SortField, QAction] = {}
        for field, label in SORT_FIELD_LABELS.items():
            action = QAction(label, self)
            action.setCheckable(True)
            action.triggered.connect(
                lambda _checked, value=field: self._set_sort_field(value)
            )
            self.sort_field_group.addAction(action)
            self.sort_field_actions[field] = action

        self.sort_ascending_action = QAction("По возрастанию", self)
        self.sort_ascending_action.setCheckable(True)
        self.sort_ascending_action.triggered.connect(
            lambda: self._set_sort_direction(False)
        )

        self.sort_descending_action = QAction("По убыванию", self)
        self.sort_descending_action.setCheckable(True)
        self.sort_descending_action.triggered.connect(
            lambda: self._set_sort_direction(True)
        )

        self.sort_direction_group = QActionGroup(self)
        self.sort_direction_group.addAction(self.sort_ascending_action)
        self.sort_direction_group.addAction(self.sort_descending_action)
        self._sync_sort_actions()

        self.addActions(
            [
                self.open_action,
                self.open_folder_action,
                self.close_action,
                self.exit_action,
                self.prev_file_action,
                self.next_file_action,
                self.prev_page_action,
                self.next_page_action,
                self.rotate_left_action,
                self.rotate_right_action,
                self.rotate_180_action,
                self.flip_horizontal_action,
                self.flip_vertical_action,
                self.reset_transform_action,
                self.zoom_in_action,
                self.zoom_out_action,
                self.reset_zoom_action,
                *self.sort_field_actions.values(),
                self.sort_ascending_action,
                self.sort_descending_action,
            ]
        )

    def _build_menu(self) -> None:
        file_menu = self.menuBar().addMenu("Файл")
        file_menu.addAction(self.open_action)
        file_menu.addAction(self.open_folder_action)
        file_menu.addAction(self.close_action)
        file_menu.addSeparator()
        file_menu.addAction(self.exit_action)

        navigation_menu = self.menuBar().addMenu("Переход")
        navigation_menu.addAction(self.prev_file_action)
        navigation_menu.addAction(self.next_file_action)
        navigation_menu.addSeparator()
        navigation_menu.addAction(self.prev_page_action)
        navigation_menu.addAction(self.next_page_action)

        view_menu = self.menuBar().addMenu("Вид")
        view_menu.addAction(self.zoom_in_action)
        view_menu.addAction(self.zoom_out_action)
        view_menu.addAction(self.reset_zoom_action)
        view_menu.addSeparator()

        sort_menu = view_menu.addMenu("Сортировка")
        for field in SORT_FIELD_LABELS:
            sort_menu.addAction(self.sort_field_actions[field])
        sort_menu.addSeparator()
        sort_menu.addAction(self.sort_ascending_action)
        sort_menu.addAction(self.sort_descending_action)

        transform_menu = self.menuBar().addMenu("Преобразование")
        transform_menu.addAction(self.rotate_left_action)
        transform_menu.addAction(self.rotate_right_action)
        transform_menu.addAction(self.rotate_180_action)
        transform_menu.addSeparator()
        transform_menu.addAction(self.flip_horizontal_action)
        transform_menu.addAction(self.flip_vertical_action)
        transform_menu.addSeparator()
        transform_menu.addAction(self.reset_transform_action)

    def _build_toolbar(self) -> None:
        toolbar = QToolBar("Основные действия", self)
        toolbar.setAllowedAreas(Qt.ToolBarArea.TopToolBarArea)
        toolbar.setFloatable(False)
        toolbar.setMovable(False)
        toolbar.setToolButtonStyle(Qt.ToolButtonStyle.ToolButtonTextOnly)

        toolbar.addAction(self.open_action)
        toolbar.addAction(self.open_folder_action)
        toolbar.addSeparator()
        toolbar.addAction(self.prev_file_action)
        toolbar.addAction(self.next_file_action)
        toolbar.addAction(self.prev_page_action)
        toolbar.addAction(self.next_page_action)
        toolbar.addSeparator()
        toolbar.addAction(self.rotate_left_action)
        toolbar.addAction(self.rotate_right_action)
        toolbar.addSeparator()
        toolbar.addWidget(self.status_label)

        self.addToolBar(Qt.ToolBarArea.TopToolBarArea, toolbar)
        self.toolbar = toolbar

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
            self._open_file_path(Path(file_path))

        self.update_controls()

    def open_folder(self) -> None:
        folder = QFileDialog.getExistingDirectory(self, "Открыть папку", "")
        if not folder:
            return
        self._open_folder_path(Path(folder))

    def _open_folder_path(self, folder_path: Path) -> bool:
        try:
            files = sorted_supported_files(folder_path, self.directory_sort)
        except OSError as exc:
            QMessageBox.warning(
                self,
                "Ошибка открытия",
                f"Папку не удалось открыть:\n{folder_path}\n\n{exc}",
            )
            return False

        if not files:
            QMessageBox.information(
                self,
                "Нет поддерживаемых файлов",
                f"В папке нет PDF или изображений:\n{folder_path}",
            )
            return False

        return self._open_file_path(files[0])

    def _open_file_path(self, file_path: Path) -> bool:
        existing_index = self._find_opened_tab(str(file_path))
        if existing_index >= 0:
            self.tabs.setCurrentIndex(existing_index)
            tab = self.current_tab()
            if tab is not None:
                tab.set_directory_sort(self.directory_sort)
            return True

        try:
            tab = DocumentTab(str(file_path), self.directory_sort)
        except Exception as exc:
            QMessageBox.warning(
                self,
                "Ошибка открытия",
                f"Файл не удалось открыть:\n{file_path}\n\n{exc}",
            )
            return False

        tab.state_changed.connect(self.update_controls)
        tab.file_changed.connect(
            lambda _path, tab_ref=tab: self._sync_tab_title(tab_ref)
        )
        index = self.tabs.addTab(tab, tab.file_path.name)
        self.tabs.setTabToolTip(index, str(tab.file_path))
        self.tabs.setCurrentIndex(index)
        tab.fit_to_viewport()
        return True

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

    def _sync_sort_actions(self) -> None:
        self.sort_field_actions[self.directory_sort.field].setChecked(True)
        self.sort_ascending_action.setChecked(not self.directory_sort.descending)
        self.sort_descending_action.setChecked(self.directory_sort.descending)

    def _set_sort_field(self, field: SortField) -> None:
        self._set_directory_sort(DirectorySort(field, self.directory_sort.descending))

    def _set_sort_direction(self, descending: bool) -> None:
        self._set_directory_sort(DirectorySort(self.directory_sort.field, descending))

    def _set_directory_sort(self, directory_sort: DirectorySort) -> None:
        if self.directory_sort == directory_sort:
            return

        self.directory_sort = directory_sort
        self._sync_sort_actions()
        for idx in range(self.tabs.count()):
            tab = self.tabs.widget(idx)
            if isinstance(tab, DocumentTab):
                tab.set_directory_sort(directory_sort)
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
        self.prev_file_action.setEnabled(enabled and tab.can_prev_file())
        self.next_file_action.setEnabled(enabled and tab.can_next_file())
        self.prev_page_action.setEnabled(enabled and tab.can_prev_page())
        self.next_page_action.setEnabled(enabled and tab.can_next_page())
        self.rotate_left_action.setEnabled(enabled)
        self.rotate_right_action.setEnabled(enabled)
        self.rotate_180_action.setEnabled(enabled)
        self.flip_horizontal_action.setEnabled(enabled)
        self.flip_vertical_action.setEnabled(enabled)
        self.reset_transform_action.setEnabled(enabled)
        self.zoom_in_action.setEnabled(enabled and tab.can_zoom_in())
        self.zoom_out_action.setEnabled(enabled and tab.can_zoom_out())
        self.reset_zoom_action.setEnabled(enabled)

        if not enabled:
            self.status_label.setText("Файл не открыт")
            return

        self.status_label.setText(tab.status_text())

    def closeEvent(self, event) -> None:
        for idx in range(self.tabs.count()):
            tab = self.tabs.widget(idx)
            if isinstance(tab, DocumentTab):
                tab.cleanup()
        super().closeEvent(event)
