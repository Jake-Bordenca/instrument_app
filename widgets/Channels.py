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