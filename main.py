import sys

from PySide6.QtWidgets import QApplication

from file_opener.main_window import MainWindow


def main() -> None:
    app = QApplication(sys.argv)
    app.setApplicationName("File Opener")
    window = MainWindow()
    window.showMaximized()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
