import instrument_app.widgets.CustomWidgets as cw
from PyQt5.QtCore import QObject, pyqtSignal
import time

###############################################################################
# The Qt signal bus
###############################################################################

class AppChannels(QObject):
    log = pyqtSignal(str)
    error = pyqtSignal(str)
    connection_changed = pyqtSignal(bool, str)
    data_received = pyqtSignal(dict)
    command_sent = pyqtSignal(str)

    def __init__(self, parent=None):
        super().__init__(parent)

###############################################################################
# The generic classes
###############################################################################

class Channel():
    def __init__(self, name, description, group, 
                 COM, readback_command=None, get_command=None, set_command=None):
        self.name = name
        self.group = group
        self.COM = COM
        self.description = description
        self.setValue = None
        self.actualValue = None
        self.readback_command = readback_command
        self.get_command = get_command
        self.set_command = set_command


class ReadbackMixin:
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

    def readback(self):
        self.COM.sendCompact(f'{self.readback_command}?')

    def updateReadback(self, message, readback):
        self.gui.updateReadback(message, readback)


class SetMixin:
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

    def write(self, value):
        message = f'{self.set_command}={value}'
        self.COM.sendCompact(message)


class GetMixin:
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

    def get(self):
        self.COM.sendCompact(f'{self.get_command}$')

    def updateSetting(self, message, response):
        self.gui.updateSetting(message, response)
   

###############################################################################
# The specific channel classes
###############################################################################

class NumericMonitor(ReadbackMixin, Channel):
    def __init__(self, name, description, group, 
                 COM, 
                 readback_command, 
                 conversion_factor, units=''):
        super().__init__(name, description, group, 
                         COM, 
                         readback_command = readback_command, 
                         get_command = None, 
                         set_command = None)
        self.units = units
        self.conversion_factor = conversion_factor
        
        self.gui = cw.QNumericMonitor(label_text = self.name, units = self.units, conversion_factor=self.conversion_factor)


class BinaryMonitor(ReadbackMixin, Channel):
    def __init__(self, name, description, group, 
                 COM, readback_command, 
                 decoder=()):
        super().__init__(name, description, group, 
                         COM, 
                         readback_command = readback_command, 
                         get_command = None, 
                         set_command = None)
        self.decoder = decoder
        
        
class NumericSettingNoReadback(GetMixin, SetMixin, Channel):
    def __init__(self, name, description, group, 
                COM, get_command, set_command, 
                default_value=0.0, min_value=0.0, max_value=0.0, offset=None, polarity=False, 
                step_values=None, units=''):
        super().__init__(name, description, group, 
                         COM, 
                         readback_command = None, 
                         get_command = get_command, 
                         set_command = set_command)
        self.value = default_value
        self.min_value = min_value
        self.max_value = max_value
        self.step_values = step_values

        self.offset = [0.0]
        if isinstance(offset, float):
            self.offset = [offset]
        elif isinstance(offset, list):
            self.offset = offset
        else:
            print(f"Invalid argument for offset in {name}")

        if self.offset is not None:
            self.write_value = str(float(self.value) - sum(self.offset))
        else:
            self.write_value = self.value

        self.gui = cw.QNumericControl(label_text = self.name, default_value = self.value, min_value = self.min_value, max_value = self.max_value)
        self.gui.box.valueConfirmed.connect(self.valueChange)
        #self.readSetting()

    def valueChange(self, value):
        if self.offset is not None:
            self.write_value = value - sum(self.offset)
        else:
            self.write_value = value
        self.write(f'{self.write_value:.1f}')

# IFOC:ISEY - isCID energy
# IFOC:IOEY - Quad energy offset
# IFOC:COEY - Collision energy

class NumericSettingWithReadback(ReadbackMixin, NumericSettingNoReadback):
    def __init__(self, name, description, group, 
                COM, readback_command, get_command, set_command, 
                default_value=0.0, min_value=0.0, max_value=0.0, offset=None, polarity=False, 
                step_values=None, units=''):
        super().__init__(name, description, group, 
                COM, get_command, set_command, 
                default_value, min_value, max_value, offset, polarity, 
                step_values, units)
        self.readback_command = readback_command


class TurboSetting(ReadbackMixin, GetMixin, SetMixin, Channel):
    def __init__(self, name, description, group, 
                 COM, readback_command, get_command, set_command):
        super().__init__(name, description, group, 
                         COM, 
                         readback_command = readback_command, 
                         get_command = get_command, 
                         set_command = set_command)
        self.switch_value = "START"

        self.gui = cw.QTurboControl(label_text = name) # Need to update QTurboControl to accept read and set commands
        self.gui.turboSwitch.connect(self.switchChange)

    def switchChange(self, value):
        if value == "START" and self.switch_value == "STOP":
            self.write('1')
        elif value == "STOP" and self.switch_value == "START":
            self.write('0')


class SwitchSetting(GetMixin, SetMixin, Channel):
    def __init__(self, name, description, group, 
                 COM, get_command, set_command, 
                 options=None, default_value=None):
        super().__init__(name, description, group, 
                         COM, 
                         readback_command = None, 
                         get_command = get_command, 
                         set_command = set_command)
        self.options = options
        self.switch_value = default_value

        self.gui = cw.QSwitchControl(label_text = name, options = options, default_value = default_value)
        self.gui.switchChanged.connect(self.switchChange)

    def switchChange(self, value):
        self.write(f'{value}')

class UserInput(Channel):
    def __init__(self, name, group, description, COM):
        super().__init__(name, group, description, COM)

        self.gui = cw.QUserInput(label_text=self.name)
        self.gui.textSubmitted.connect(self.write)

    @staticmethod
    def _validate_message(message):
        if not isinstance(message, str):
            return None, "Input must be text."

        cleaned = message.strip()
        if cleaned == '':
            return None, "Command cannot be blank."

        if any(ch in cleaned for ch in ('@', '\r', '\n')):
            return None, "Do not include checksum or line terminators in commands."

        if any(ord(ch) < 32 or ord(ch) == 127 for ch in cleaned):
            return None, "Command includes unsupported control characters."

        try:
            cleaned.encode('ascii')
        except UnicodeEncodeError:
            return None, "Command must contain ASCII characters only."

        return cleaned, None

    @staticmethod
    def _format_response(response):
        if response is None:
            return False, "No response or protocol/checksum failure."

        if isinstance(response, tuple):
            if len(response) == 0:
                return False, "Empty response."
            if len(response) >= 2 and response[0] is None and response[1] is None:
                return False, "Instrument returned an empty response."
            payload = response[0]
        else:
            payload = response

        if payload is None:
            return False, "No response payload returned."

        if isinstance(payload, str):
            text = payload.strip()
        elif isinstance(payload, list):
            text = "; ".join(str(item) for item in payload if str(item).strip() != '')
        else:
            text = str(payload).strip()

        if text == '':
            return False, "Response payload is empty."
        return True, text

    def write(self, message):
        print("UserInput COM:", repr(self.COM))
        print("UserInput COM type:", type(self.COM))
        print("UserInput module:", type(self.COM).__module__)
        print("UserInput class:", type(self.COM).__name__)

        command, error = self._validate_message(message)
        if error:
            self.gui.updateReadback(error, '')
            self.gui.setStatus(error, error=True)
            return

        try:
            response = self.COM.sendCompact(command)
        except Exception as exc:
            error_message = f"Serial error: {exc}"
            self.gui.updateReadback(error_message, '')
            self.gui.setStatus(error_message, error=True)
            return

        self.gui.clearInput()
        success, details = self._format_response(response)
        if success:
            self.gui.updateReadback(f"Sent: {command}", details)
            self.gui.setStatus("Command sent successfully.", error=False)
        else:
            self.gui.updateReadback(f"Sent: {command}", details)
            self.gui.setStatus(details, error=True)

    def update(self, message, readback):
        self.gui.updateReadback(message, readback)




###############################################################################






class Monitor(Channel):
    def __init__(self, name, group, 
                 COM, readback_command, 
                 description=''):
        super().__init__(name, group, COM, description = description)
        self.readback_command = readback_command
        self.value = None
    
    def sendRead(self):
        self.COM.sendCompact(f'{self.readback_command}?')

    def update(self, message, readback):
        self.gui.updateReadback(message, readback)


class Setting(Monitor):
    def __init__(self, name, group, 
                 COM, readback_command, set_command, 
                 description=''):
        super().__init__(name, group, COM, readback_command, description = description)
        self.set_command = set_command

    def write(self, value):
        message = f'{self.set_command}={value}'
        self.COM.sendCompact(message)

    def update(self, message, response):
        self.gui.updateSetting(message, response)
