from PyQt5.QtWidgets import QWidget, QLabel, QVBoxLayout, QLineEdit, QHBoxLayout, QProgressBar, QPushButton
from PyQt5.QtCore import Qt, pyqtSignal, QEvent
from PyQt5.QtGui import QDoubleValidator

class QPressureMonitor(QWidget):
    def __init__(self, label_text="default", serial_command="VACU:SRPV", units="Torr", parent=None):
        super().__init__(parent)

        # Create the subwidgets
        self.title_label = QLabel(label_text)
        self.pressure = QLabel()

        # Set the serial command and the pressure units
        self.serial_command = serial_command
        self.units = units

        # Set up the layout.  We want a label with the pressure text below it
        layout = QVBoxLayout()
        layout.addWidget(self.title_label)
        layout.addWidget(self.pressure)
        # Apply the layout
        self.setLayout(layout)

    def get_update_message(self):
        return f"{self.serial_command}?"

    def update(self, pressure):
        self.pressure.setText(f"{float(pressure[0])*.76:.3e} {self.units}")
