"""
Custom Qt widgets for instrument control/DAQ software

Written for Qt5

Author: Chris Johnson

Changelog:
    062124 - Work begun
    090325 - Adapting for inclusion in the Channels classes
"""

from PyQt5.QtWidgets import QWidget, QLabel, QVBoxLayout, QLineEdit, QHBoxLayout, QProgressBar, QPushButton, QComboBox
from PyQt5.QtCore import Qt, pyqtSignal, QEvent
from PyQt5.QtGui import QDoubleValidator
from math import floor, log10

###############################################################################
# The generic widgets that serve as bases
###############################################################################

class CustomLineEditWithArrows(QWidget):
    valueConfirmed = pyqtSignal(float)

    def __init__(self, current_value, min_value, max_value, step_values=None, 
                 units='', *args, **kwargs):
        super().__init__(*args, **kwargs)

        # Load the incoming parameters
        self.min_value = min_value
        self.max_value = max_value
        self.previous_value = current_value  # To store the previous valid value
        self.current_value = current_value
        self.units = units

        # Get the step sizes
        if isinstance(step_values, type(None)):
            self.step_values = self.generate_step_values(self.max_value)
        elif isinstance(step_values, list):
            self.step_values = step_values
        self.current_step_index = 0

        # Set up the text box
        self.text_box = QLineEdit(*args, **kwargs)
        self.text_box.setFixedWidth(64)
        self.text_box.setText(self.format_value(self.current_value))
        self.text_box.setToolTip(f"({min_value:.1f}...{max_value:.1f})")
        self.text_box.setValidator(QDoubleValidator(min_value, max_value, 1))  # Validate input as double
        self.text_box.installEventFilter(self)

        # Create a label for the units
        self.unit_label = QLabel(self.units)
        self.unit_label.setFixedWidth(16)

        # Create a label for the step size
        self.step_label = QLabel()
        self.step_label.setFixedWidth(32)  # Ensure the label always has the same width
        self.update_step_label()  # Set the initial step value display
        
        # Set up the layout
        layout = QHBoxLayout()
        layout.addWidget(self.text_box)
        layout.addWidget(self.unit_label)
        layout.addWidget(self.step_label)
        self.setLayout(layout)

    def keyPressEvent(self, event):
        if event.key() in (Qt.Key.Key_Return, Qt.Key.Key_Enter):
            # The user has already changed the text in the box, so the current text is the new value
            try:
                self.previous_value = self.current_value  # Update previous value
                self.current_value = float(self.text_box.text())
                #self.setText(self.format_value(self.current_value))
                self.valueConfirmed.emit(self.current_value)
            except ValueError:
                self.text_box.setText(self.format_value(self.previous_value))  # Reset to previous valid value
            return True
        elif event.key() in (Qt.Key.Key_W, Qt.Key.Key_S):
            # The user is requesting the value to change, so the current text is the previous value
            try:
                self.previous_value = float(self.text_box.text())
                step_value = self.step_values[self.current_step_index]
                if event.key() == Qt.Key.Key_W:
                    new_value = self.previous_value + step_value
                elif event.key() == Qt.Key.Key_S:
                    new_value = self.previous_value - step_value
                # Clamp to min/max if the new value is out of range
                new_value = min(max(new_value, self.min_value), self.max_value)
                if new_value != self.previous_value:  # Only emit signal if the value changes
                    self.text_box.setText(self.format_value(new_value))
                    self.current_value = new_value
                    self.valueConfirmed.emit(new_value)
            except ValueError:
                pass  # Ignore invalid input
            return True
        elif event.key() in (Qt.Key.Key_A, Qt.Key.Key_D):
            if event.key() == Qt.Key.Key_A:
                self.current_step_index = max(0, self.current_step_index - 1)
            elif event.key() == Qt.Key.Key_D:
                self.current_step_index = min(len(self.step_values) - 1, self.current_step_index + 1)
            self.update_step_label()
            return True
        else:
            super().keyPressEvent(event)
        return False

    def eventFilter(self, obj, event):
        if obj is self.text_box and event.type() == QEvent.KeyPress:
            return self.keyPressEvent(event)
        return super().eventFilter(obj, event)

    def update_step_label(self):
        step_value = self.step_values[self.current_step_index]
        self.step_label.setText(f"±{step_value:.1f}")

    @property
    def value(self):
        return self.current_value

    @staticmethod
    def generate_step_values(max_value):
        step_values = []

        if max_value > 0: 
            order = floor(log10(max_value))
            step = 10**(order - 3)
            while step <= max_value:
                step_values.append(step)
                step *= 10
            return step_values
            
        elif max_value==0:
            print("Max Value = 0!")

        else:
            print("Something's wrong!")    

    @staticmethod
    def format_value(value):
        return f"{value:.1f}"

###############################################################################
# The actual widgets
###############################################################################

class QNumericControl(QWidget):
    def __init__(self, label_text="default", 
                 default_value=0.0, min_value=0.0, max_value=1000.0, step_values=None, 
                 units='', parent=None, *args, **kwargs):
        super().__init__(parent)

        # We need a variable to hold the set voltage as a float
        self.value = default_value
        self.units = units

        # Create a QLabel for the title
        self.title_label = QLabel(label_text)

        # Create a CustomLineEditWithArrows (text box)
        self.box = CustomLineEditWithArrows(self.value, min_value, max_value, step_values, units = self.units)

        # Create a QLabel to display the eradback
        self.readback = QLabel()

        # Vertical layout to hold the title label and horizontal layout
        v_layout = QVBoxLayout()
        v_layout.addWidget(self.title_label)
        v_layout.addWidget(self.box)
        v_layout.addWidget(self.readback)
        # Apply the layout
        self.setLayout(v_layout)
        
    def setProperties(self, label_text, default_value, min_value, max_value):
        self.title_label.setText(label_text)
        self.box.min_value = min_value
        self.box.max_value = max_value
        self.box.setToolTip(f"({min_value:.1f}...{max_value:.1f})")
        self.box.setText(f"{default_value:.1f}")
        self.box.previous_value = default_value
        self.box.setValidator(QDoubleValidator(min_value, max_value, 1))

    def updateReadback(self, response):
        self.readback.setText(response[0])

        # Check if the readback is more than 5% different than the set value
        if (self.value - float(response[0]))/self.value < 0.05:
            # Make the readback green
            self.readback.setStyleSheet('color: green;')
        else:
            # Make the readback red
            self.readback.setStyleSheet('color: red;')

    def updateSetting(self, response):
        self.box.text_box.setText(f"{float(response[0]):.1f}")


class QTurboControl(QWidget):
    turboSwitch = pyqtSignal(str)

    def __init__(self, label_text="default", parent=None):
        super().__init__(parent)

        # Create the subwidgets
        self.title_label = QLabel(label_text)
        self.speed = QProgressBar()
        self.power = QLabel()
        self.switch = QPushButton(text = "START")
        self.switch.clicked.connect(self.clickEvent)

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
        display_layout.addWidget(self.switch)
        layout = QVBoxLayout()
        # The title is above the whole thing
        title_layout = QHBoxLayout()
        title_layout.addWidget(self.title_label)
        layout.addLayout(title_layout)
        layout.addLayout(display_layout)
        # Apply the layout
        self.setLayout(layout)

    def updateReadback(self, response):
        if len(response) == 1:
            onoff = response
        elif len(response) == 3:
            # Unpack the response
            onoff, speed, power = response
            # Update the speed and power displays
            self.speed.setValue(int(speed))
            self.power.setText(f'{power}%')
        else:
            print("Wrong number of responses to turbo read")

        # Deal with the on/off stuff
        if onoff == "0":
            self.switch.text = "STOP"
            self.switch.setStyleSheet("background-color: lightgreen;")
        elif onoff == "1":
            self.switch.text = "START"
            self.switch.setStyleSheet("background-color: red;")
        else:
            print("Invalid response to turbo switch")

    def updateSetting(self, response):
        # Deal with the on/off stuff
        if response == "0":
            self.switch.text = "STOP"
            self.switch.setStyleSheet("background-color: lightgreen;")
        elif response == "1":
            self.switch.text = "START"
            self.switch.setStyleSheet("background-color: red;")
        else:
            print("Invalid response to turbo switch")

    def clickEvent(self, clicked):
        self.turboSwitch.emit(clicked)


class QSwitchControl(QWidget):
    switchChanged = pyqtSignal(int)

    def __init__(self, label_text, options, default_value, parent=None):
        super().__init__(parent)

        self.title_label = QLabel(label_text)
        self.options = options
        self.value = QComboBox()
        self.value.addItems(self.options)
        self.value.activated.connect(self.comboEvent)
        self.updateSetting([self.options.index(default_value)])

        layout = QVBoxLayout()
        layout.addWidget(self.title_label)
        layout.addWidget(self.value)
        self.setLayout(layout)

    def updateSetting(self, response):
        print(response, self.options)
        if response[0] in (1, 2, 3, 4, 5, 6):
            self.value.setCurrentIndex(int(response[0]))
        else:
            print(f"Default value not found in list of options for {self.title_label} combo box.")
        self.value.setCurrentIndex(int(response[0]))

    def comboEvent(self, selection):
        self.switchChanged.emit(selection)
        

class QNumericMonitor(QWidget):
    def __init__(self, label_text="default", units="Torr", parent=None):
        super().__init__(parent)

        # Create the subwidgets
        self.title_label = QLabel(label_text)
        self.value = QLabel()
        self.units = units

        # Set up the layout.  We want a label with the pressure text below it
        layout = QVBoxLayout()
        layout.addWidget(self.title_label)
        layout.addWidget(self.value)
        # Apply the layout
        self.setLayout(layout)

    def updateReadback(self, response):
        self.value.setText(f"{float(response[0])*.76:.3e} {self.units}")
