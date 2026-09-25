import instrument_app.widgets.CustomWidgets as cw

###############################################################################
# The generic classes
###############################################################################

class Channel():
    def __init__(self, name, group, 
                 COM, 
                 description=''):
        self.name = name
        self.group = group
        self.COM = COM
        self.description = description


class Monitor(Channel):
    def __init__(self, name, group, 
                 COM, readback_command, 
                 description=''):
        super().__init__(name, group, COM, description = description)
        self.readback_command = readback_command
    
    def readActual(self):
        print(self.name)
        response, full_response = self.COM.sendCompact(f'{self.readback_command}?')
        self.parse(response)

    def parse(self, response):
        self.gui.updateReadback(response)
        

class Setting(Monitor):
    def __init__(self, name, group, 
                 COM, readback_command, set_command, 
                 description=''):
        super().__init__(name, group, COM, readback_command, description = description)
        self.set_command = set_command

    def readSetting(self):
        response, full_response = self.COM.sendCompact(f'{self.readback_command}?')
        self.gui.updateSetting(response)

    def write(self, value):
        message = f'{self.set_command}={value}'
        response, full_response = self.COM.sendCompact(message)
        if response is None or full_response is None:
            return
        print(full_response[0], message)
        if message in full_response[0] or full_response[0] in message:
            print('Command successful')
            self.gui.updateSetting(response)
        else:
            print('Command write', message, 'returned', full_response)


###############################################################################
# The specific channel classes
###############################################################################

class NumericMonitor(Monitor):
    def __init__(self, name, group, 
                 COM, readback_command, 
                 conversion_factor=(1,0), 
                 units='', description=''):
        super().__init__(name, group, COM, readback_command, description = description)
        self.units = units
        self.conversion_factor = conversion_factor
        
        self.gui = cw.QNumericMonitor(label_text = self.name, units = self.units)


class BinaryMonitor(Monitor):
    def __init__(self, name, group, COM, readback_command, description='', decoder=(), *args, **kwargs):
        super().__init__(name, group, COM, readback_command, description = description, *args, **kwargs)
        self.decoder = decoder
        
        
class NumericSetting(Setting):
    def __init__(self, name, group, COM, readback_command, set_command, description='', 
                 default_value=0.0, min_value=0.0, max_value=0.0, step_values=None, units='',
                 *args, **kwargs):
        super().__init__(name, group, COM, readback_command, set_command, description = description, *args, **kwargs)
        self.value = default_value
        self.min_value = min_value
        self.max_value = max_value
        self.step_values = step_values

        self.gui = cw.QNumericControl(label_text = self.name, default_value = self.value, min_value = self.min_value, max_value = self.max_value)
        self.gui.box.valueConfirmed.connect(self.valueChange)
        #self.readSetting()

    def valueChange(self, value):
        print('Value Changed')
        self.write(f'{value:.1f}')


class TurboSetting(Setting):
    def __init__(self, name, group, COM, readback_command, set_command, description=''):
        super().__init__(name, group, COM, readback_command, set_command, description = description)
        self.switch_value = "START"

        self.gui = cw.QTurboControl(label_text = name) # Need to update QTurboControl to accept read and set commands
        self.gui.turboSwitch.connect(self.switchChange)

    def switchChange(self, value):
        if value == "START" and self.switch_value == "STOP":
            self.write('1')
        elif value == "STOP" and self.switch_value == "START":
            self.write('0')

class SwitchSetting(Setting):
    def __init__(self, name, group, COM, set_command, description='', options=None, default_value=None):
        super().__init__(name, group, COM, readback_command=None, set_command=set_command, description = description)
        self.options = options
        self.switch_value = default_value

        self.gui = cw.QSwitchControl(label_text = name, options = options, default_value = default_value)
        self.gui.switchChanged.connect(self.switchChange)

    def switchChange(self, value):
        self.write(f'{value}')


class UserInput(Channel):
    def __init__(self, name, group, COM, description=''):
        super().__init__(name, group, COM, description=description)
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