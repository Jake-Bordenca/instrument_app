from PyQt5.QtWidgets import QWidget, QLabel, QVBoxLayout, QLineEdit, QHBoxLayout, QProgressBar, QPushButton
from PyQt5.QtCore import Qt, pyqtSignal, QEvent
from PyQt5.QtGui import QDoubleValidator

class QTurboControl(QWidget):
    def __init__(self, label_text="default", serial_prefix="TP_1", parent=None):
        super().__init__(parent)

        # Create the subwidgets
        self.title_label = QLabel(label_text)
        self.speed = QProgressBar()
        self.power = QLabel()
        self.switch = QPushButton()

        # Get the serial prefix
        self.serial_prefix = serial_prefix

        # Set up the layout.  Each display has a label above it, and they are in a horizontal row.
        # The speed section contains a label and progress bar
        speed_layout = QVBoxLayout()
        speed_layout.addWidget(QLabel("Speed"))
        speed_layout.addWidget(self.speed)
        # The power section contains a label and text for the power
        power_layout = QVBoxLayout()
        power_layout.addWidget(QLabel("Power"))
        power_layout.addWidget(self.power)
        # The speed section and power section should be side by side
        display_layout = QHBoxLayout()
        display_layout.addLayout(speed_layout)
        display_layout.addLayout(power_layout)
        layout = QVBoxLayout()
        # The title is above the whole thing.
        title_layout = QHBoxLayout()
        title_layout.addWidget(self.title_label)
        layout.addLayout(title_layout)
        layout.addLayout(display_layout)
        # Apply the layout
        self.setLayout(layout)

    def get_update_message(self):
        # Ask for the state, the speed, and the power in one line
        return f"{self.serial_prefix}:MOSW?;{self.serial_prefix}:ROTR?;{self.serial_prefix}:POWR?"

    def update(self, response):
        # Unpack the response
        onoff, speed, power = response

        # Deal with the on/off stuff
        if onoff == "1":
            self.switch.text = "STOP"
            self.switch.setStyleSheet("background-color: lightgreen;")
        else:
            self.switch.text = "START"
            self.switch.setStyleSheet("background-color: red;")
        
        # Update the speed and power displays
        self.speed.setValue(int(speed))
        self.power.setText(f'{power} %')
