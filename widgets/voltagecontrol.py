from PyQt5.QtWidgets import QWidget, QLabel, QVBoxLayout, QLineEdit, QHBoxLayout, QProgressBar, QPushButton
from PyQt5.QtCore import Qt, pyqtSignal, QEvent
from PyQt5.QtGui import QDoubleValidator

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
        #self.text_box.keyPressEvent = self.keyPressEvent
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
        #else:
            #self.text_box.keyPressEvent(event)
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
        step = 0.1
        while step <= max_value:
            step_values.append(step)
            step *= 10
        return step_values

    @staticmethod
    def format_value(value):
        return f"{value:.1f}"

class QVoltageControl(QWidget):
    changeRequested = pyqtSignal(str)

    def __init__(self, label_text="Voltage", serial_command_write=None, serial_command_readback=None, 
                 default_value=0.0, min_value=0.0, max_value=1000.0, step_values=None, 
                 units='', parent=None, *args, **kwargs):
        super().__init__(parent)

        # We need a variable to hold the set voltage as a float
        self.value = default_value
        self.units = units

        # The serial commands for this voltage
        self.serial_command_write = serial_command_write
        self.serial_command_readback = serial_command_readback

        # Create a QLabel for the title
        self.title_label = QLabel(label_text)

        # Create a CustomLineEditWithArrows (text box)
        self.box = CustomLineEditWithArrows(self.value, min_value, max_value, step_values, units = self.units)
        self.box.valueConfirmed.connect(self.placeholder_function)  # Connect the valueConfirmed signal to placeholder_function

        # Create a QLabel to display the eradback
        self.readback = QLabel()

        # Vertical layout to hold the title label and horizontal layout
        v_layout = QVBoxLayout()
        v_layout.addWidget(self.title_label)
        v_layout.addWidget(self.box)
        v_layout.addWidget(self.readback)
        # Apply the layout
        self.setLayout(v_layout)
        
    def set_properties(self, label_text, default_value, min_value, max_value):
        self.title_label.setText(label_text)
        self.box.min_value = min_value
        self.box.max_value = max_value
        self.box.setToolTip(f"({min_value:.1f}...{max_value:.1f})")
        self.box.setText(f"{default_value:.1f}")
        self.box.previous_value = default_value
        self.box.setValidator(QDoubleValidator(min_value, max_value, 1))

    def get_readback_message(self):
        return f'{self.serial_command_readback}?'

    def update_readback(self, response):
        self.readback.setText(response[0])

        # Check if the readback is more than 5% different than the set value
        if (self.value - float(response[0]))/self.value < 0.05:
            # Make the readback green
            self.readback.setStyleSheet('color: green;')
        else:
            # Make the readback red
            self.readback.setStyleSheet('color: red;')

    def get_assign_message(self):
        return f'{self.serial_command_write}={self.value}'

    def placeholder_function(self, value):
        # Placeholder function to be called when the value changes
        print(f"Voltage value changed: {value:.1f}")
