"""
Custom Qt widgets for instrument control/DAQ software

Written for Qt5

Author: Chris Johnson

Changelog:
    062124 - Work begun
    090325 - Adapting for inclusion in the Channels classes
"""

from math import floor, log10

from PyQt5.QtCore import QEvent, QSize, Qt, pyqtSignal
from PyQt5.QtGui import QDoubleValidator
from PyQt5.QtWidgets import (
    QComboBox,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QProgressBar,
    QPushButton,
    QSizePolicy,
    QVBoxLayout,
    QWidget,
)

from instrument_app.theme import style

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
        self.text_box.setFixedWidth(100)
        self.text_box.setText(self.format_value(self.current_value))
        self.text_box.setToolTip(f"({min_value:.1f}...{max_value:.1f})")
        self.text_box.setValidator(QDoubleValidator(min_value, max_value, 1))  # Validate input as double
        self.text_box.installEventFilter(self)

        # Create a label for the units
        self.unit_label = QLabel(self.units)
        self.unit_label.setFixedWidth(50)

        # Create a label for the step size
        self.step_label = QLabel()
        self.step_label.setFixedWidth(75)  # Ensure the label always has the same width
        self.update_step_label()  # Set the initial step value display
        
        # Set up the layout
        layout = QHBoxLayout()
        layout.addWidget(self.text_box)
        layout.addWidget(self.unit_label)
        layout.addWidget(self.step_label)
        self.setLayout(layout)
        self.setFixedSize(300, 100)

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
        order = floor(log10(max_value))
        step = 10**(order - 3)
        while step <= max_value:
            step_values.append(step)
            step *= 10
        return step_values

    @staticmethod
    def format_value(value):
        return f"{value:.1f}"

###############################################################################
# The actual widgets
###############################################################################
class HeaderLabel(QLabel):
    """A reusable main header label."""
    def __init__(self, text="", parent=None):
        super().__init__(text, parent)

class QNumericControl(QWidget):
    def __init__(self, label_text="default", 
                 default_value=0.0, min_value=0.0, max_value=1000.0, step_values=None, 
                 units='', parent=None, channel=None, *args, **kwargs):
        super().__init__(parent)

        # We need a variable to hold the set voltage as a float
        self.set_value = default_value
        self.actual_value = None
        self.units = units

        # Create a QLabel for the title
        self.title_label = HeaderLabel(label_text)
        self.title_label.setFixedWidth(400)

        # Create a CustomLineEditWithArrows (text box)
        self.box = CustomLineEditWithArrows(self.set_value, min_value, max_value, step_values, units = self.units)
        self.box.setStyleSheet('background:transparent;')

        # Create a QLabel to display the readback
        self.readback = QLabel()
        self.readback.setFixedWidth(400)

        # Vertical layout to hold the title label and horizontal layout
        v_layout = QVBoxLayout()
        v_layout.addWidget(self.title_label)
        v_layout.addWidget(self.box)
        v_layout.addWidget(self.readback)
        v_layout.setSpacing(10)

        # Apply the layout
        self.setLayout(v_layout)
        self.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Fixed)
        
        
    def setProperties(self, label_text, default_value, min_value, max_value):
        self.title_label.setText(label_text)
        self.box.min_value = min_value
        self.box.max_value = max_value
        self.box.setToolTip(f"({min_value:.1f}...{max_value:.1f})")
        self.box.setText(f"{default_value:.1f}")
        self.box.previous_value = default_value
        self.box.setValidator(QDoubleValidator(min_value, max_value, 1))

    def updateReadback(self, message, value):
        if value is None:
            return
        #print(value)
        # Kludge, fix this later
        # if value[0].find('/') != -1:
        #     return
        # elif not isinstance(value, int) and not isinstance(value, float):
        #     value = 0.0
        converted_value = float(value)
        self.readback.setText(str(value))

        # Check if the readback is more than 5% different than the set value
        if (self.set_value - converted_value)/max(self.set_value, 0.01) < 0.05:
            # Make the readback green
            self.readback.setStyleSheet('color: green;')
        else:
            # Make the readback red
            self.readback.setStyleSheet('color: red;')

        self.actual_value = converted_value

    def updateSetting(self, message, value):
        converted_value = float(value)
        self.box.text_box.setText(f"{converted_value:.1f}")
        self.set_value = converted_value

    def getSetValue(self):
        return self.set_value

    def getActualValue(self):
        return self.actual_value

class QTurboControl(QWidget):
    turboSwitch = pyqtSignal(str)

    def __init__(self, label_text="default", parent=None, channel=None):
        super().__init__(parent)

        # Create the subwidgets
        self.title_label = HeaderLabel(label_text)
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
        self.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Fixed)

    def updateReadback(self, message, value):
        # if len(response) == 1:
        #     onoff = response
        # elif len(response) == 3:
        #     # Unpack the response
        #     onoff, speed, power = response
        #     # Update the speed and power displays
        #     self.speed.setValue(int(speed))
        #     self.power.setText(f'{power}%')
        # else:
        #     print("Wrong number of responses to turbo read")

        if 'ROTR' in message:
            self.speed.setValue(int(value))
        elif 'POWR' in message:
            self.power.setText(f'{value}%')
        elif 'MOSW' in message:
            # Deal with the on/off stuff
            if value == "0":
                self.switch.text = "STOP"
                self.switch.setStyleSheet("background-color: lightgreen;")
            elif value == "1":
                self.switch.text = "START"
                self.switch.setStyleSheet("background-color: red;")
            else:
                print("Invalid response to turbo switch")
        else:
            print(f"Got an unexpected message {message} for {self.title_label.text}")

    def clickEvent(self, clicked):
        self.turboSwitch.emit(clicked)

    def getStatus(self):
        return {'Switch': 'On', 'Speed': self.speed.value, 'Power': int(self.power.text.rstrip('%'))}

class QSwitchControl(QWidget):
    switchChanged = pyqtSignal(int)

    def __init__(self, label_text, options, default_value, parent=None):
        super().__init__(parent)

        self.title_label = HeaderLabel(label_text)
        self.options = options
        self.value = QComboBox()
        self.value.addItems(self.options)
        self.value.activated.connect(self.comboEvent)
        self.updateSetting(None, str(self.options.index(default_value)))

        layout = QVBoxLayout()
        layout.addWidget(self.title_label)
        layout.addWidget(self.value)
        self.setLayout(layout)
        self.setFixedWidth(400)
        self.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Fixed)

    def updateSetting(self, message, value):
        response = int(value)
        if response == self.value.currentIndex():
            return
        if response in (0, 1, 2, 3, 4, 5, 6):
            self.value.setCurrentIndex(response)
        else:
            print(f"Default value not found in list of options for {self.title_label} combo box.")
        #self.value.setCurrentIndex(response)

    def comboEvent(self, selection):
        self.switchChanged.emit(selection)

    def getSetValue(self):
        return self.value.currentText
        
class QNumericMonitor(QWidget):
    def __init__(self, conversion_factor, units, label_text="default",  parent=None):
        super().__init__(parent)

        # Create the subwidgets
        self.title_label = HeaderLabel(label_text)
        self.value = QLabel()
        self.conversion_factor = conversion_factor
        self.units = units

        # Set up the layout.  We want a label with the pressure text below it
        layout = QVBoxLayout()
        layout.addWidget(self.title_label)
        layout.addWidget(self.value)
        # Apply the layout
        self.setLayout(layout)
        self.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Fixed)

    def updateReadback(self, message, value):
        #print(f'in numericMonitor for {message}')
        self.value.setText(f"{float(value) * float(self.conversion_factor):.3e} {self.units}")

    def getActualValue(self):
        return float(self.value.text)

class QGaugeDisplay(QGroupBox):
    def __init__(self, title, value="0.000", unit=""):
        super().__init__(title)

        layout = QVBoxLayout()

        # Create horizontal layout for value and status indicator
        value_layout = QHBoxLayout()

        self.value_label = QLabel(value)
        self.value_label.setObjectName("value")
        self.value_label.setStyleSheet(
            f"color: {style.TXT_STRONG}; font-size: 28px; font-weight: bold;"
        )
        value_layout.addWidget(self.value_label)

        # Add stretch to push status indicator to the right
        value_layout.addStretch()

        # Status indicator light
        self.status_indicator = QLabel("●")
        self.status_indicator.setStyleSheet(
            f"color: {style.BAD}; font-size: 24px; font-weight: bold;"
        )
        value_layout.addWidget(self.status_indicator)
        layout.addLayout(value_layout)

        self.unit_label = QLabel(unit)
        self.unit_label.setStyleSheet(
            f"color: {style.GRAY}; font-size: 10px;"
        )
        layout.addWidget(self.unit_label)

        self.setLayout(layout)

    def set_value(self, text):
        self.value_label.setText(text)

    def set_unit(self, text):
        self.unit_label.setText(text)

    def set_status(self, energized):
        """Set the status indicator color based on whether the gauge is energized."""
        if energized:
            self.status_indicator.setStyleSheet(
                f"color: {style.GOOD}; font-size: 24px; font-weight: bold;"
            )
        else:
            self.status_indicator.setStyleSheet(
                f"color: {style.BAD}; font-size: 24px; font-weight: bold;"
            )

class QPumpControl(QGroupBox):
    runClicked = pyqtSignal()
    stopClicked = pyqtSignal()

    def __init__(self, title, show_buttons=True):
        super().__init__(title)

        layout = QVBoxLayout()

        status_layout = QHBoxLayout()
        status_layout.addWidget(QLabel(title))
        status_layout.addStretch()

        self.status_label = QLabel("NO")
        self.status_label.setObjectName("status")
        status_layout.addWidget(self.status_label)
        layout.addLayout(status_layout)

        self.run_btn = None
        self.stop_btn = None
        if show_buttons:
            button_layout = QHBoxLayout()
            self.run_btn = QPushButton("RUN")
            self.run_btn.clicked.connect(self.runClicked.emit)
            self.run_btn.setObjectName("run")
            button_layout.addWidget(self.run_btn)

            self.stop_btn = QPushButton("STOP")
            self.stop_btn.clicked.connect(self.stopClicked.emit)
            self.stop_btn.setObjectName("stop")
            button_layout.addWidget(self.stop_btn)
            layout.addLayout(button_layout)

        self.setLayout(layout)
        self.apply_styles()
        self.set_status("NO")

    def apply_styles(self):
        if self.run_btn is None:
            return
        self.run_btn.setStyleSheet(
            f"background-color: {style.GOOD}; color: {style.TXT_STRONG}; "
            "padding: 8px; font-size: 11px; font-weight: bold; border-radius: 3px;"
        )
        self.stop_btn.setStyleSheet(
            f"background-color: {style.BAD}; color: {style.TXT_STRONG}; "
            "padding: 8px; font-size: 11px; font-weight: bold; border-radius: 3px;"
        )

    def set_status(self, status):
        self.status_label.setText(status)
        # Update button texts based on status
        if self.run_btn is not None:
            if status.upper() == "OK":
                self.run_btn.setText("RUNNING")
                self.stop_btn.setText("STOPPED")
            else:
                self.run_btn.setText("RUN")
                self.stop_btn.setText("STOP")
        if status == "OK":
            self.status_label.setStyleSheet(
                f"padding: 3px 8px; background-color: {style.GOOD}; "
                f"color: {style.TXT_STRONG}; border-radius: 3px; font-size: 10px;"
            )
        else:
            self.status_label.setStyleSheet(
                f"padding: 3px 8px; background-color: {style.BAD}; "
                f"color: {style.TXT_STRONG}; border-radius: 3px; font-size: 10px;"
            )

class QUserInput(QWidget):
    valueConfirmed = pyqtSignal(str)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.text_box = QLineEdit(*args, **kwargs)

        self.text_box.setPlaceholderText("Enter your text here...")
        # 3. Create a Button to capture text
        btn = QPushButton("Submit", self)
        btn.clicked.connect(self.get_text)
            
        # 4. Assemble Layout
        layout = QVBoxLayout()
        layout.addWidget(self.text_box)
        layout.addWidget(btn)
        self.readback = QLabel()
        self.readback.setFixedWidth(400)
        layout.addWidget(self.readback)
        self.setLayout(layout)
        
    def get_text(self):
        # 5. Retrieve text using .text()
        user_input = self.text_box.text()
        print(f"User typed: {user_input}")

    def updateReadback(self, message, value):
        if value is None:
            return
        self.readback.setText(str(value))