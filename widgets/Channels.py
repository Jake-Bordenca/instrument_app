import instrument_app.widgets.CustomWidgets as cw

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
