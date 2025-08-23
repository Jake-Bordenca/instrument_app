
import sys
from PyQt5.QtWidgets import QApplication, QMainWindow, QTabWidget
from instrument_app.services.serial_manager import SerialManager
from instrument_app.services.data_recorder import DataRecorder
from instrument_app.pages.pressure_page import PressureInterlockPage
from instrument_app.pages.cdms_page import CDMSPage
from instrument_app.theme import style

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Instrument Control")
        self.resize(1280, 800)
        tabs=QTabWidget()
        self.setCentralWidget(tabs)

        # shared services
        self.serial = SerialManager()
        self.rec    = DataRecorder(root="data")

        # pages
        self.pressure = PressureInterlockPage(self.serial, self.rec)
        self.cdms     = CDMSPage()

        tabs.addTab(self.pressure, "Pressures / Interlocks")
        tabs.addTab(self.cdms, "CDMS")

    def closeEvent(self, ev):
        try:
            self.serial.disconnect()
        finally:
            super().closeEvent(ev)

if __name__ == "__main__":
    app = QApplication(sys.argv)

    # Global look: dark background everywhere + tab pane
    app.setStyleSheet(f"""
        QMainWindow {{
            background: {style.BG};
            color: {style.TXT};
        }}
        QTabWidget::pane {{
            background: {style.BG};
            border: 0px;
        }}
        QTabBar::tab {{
            background: {style.BTN_BG};
            color: {style.TXT};
            border: 1px solid {style.BTN_BORDER};
            padding: 6px 10px;
            margin-right: 6px;
            border-top-left-radius: 8px;
            border-top-right-radius: 8px;
        }}
        QTabBar::tab:selected {{
            background: {style.BTN_BG_DOWN};
        }}
    """)

    win = MainWindow()
    win.show()
    sys.exit(app.exec_())
