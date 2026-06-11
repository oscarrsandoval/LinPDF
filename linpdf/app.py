import sys
from PySide6.QtWidgets import QApplication
from PySide6.QtCore import Qt
from PySide6.QtGui import QFont

from linpdf.main_window import MainWindow
from linpdf.config import Config


class Application:
    def __init__(self, argv):
        QApplication.setAttribute(Qt.AA_EnableHighDpiScaling, True)
        QApplication.setAttribute(Qt.AA_UseHighDpiPixmaps, True)

        self.qt_app = QApplication(argv)
        self.qt_app.setApplicationName("LinPDF")
        self.qt_app.setOrganizationName("LinPDF")
        self.qt_app.setApplicationVersion("0.1.0")

        font = QFont("Noto Sans", 9)
        self.qt_app.setFont(font)

        self.config = Config()

        self.main_window = MainWindow(self)

    def run(self):
        self.main_window.show()
        return self.qt_app.exec()
