import yaml
import time
import instrument_app.widgets.Channels as ch
from PyQt5.QtWidgets import (
     QWidget, QVBoxLayout, QHBoxLayout, QScrollArea, QSizePolicy, QTabWidget, QMessageBox
)
from PyQt5.QtCore import QTimer, QSize
from instrument_app.util import SerialComms

# new imports for diagnostics/retries
import serial.tools.list_ports
import traceback

def load_config(filename="instrument_app\\config\\setup_Compact.yaml"):
    """
    Loads a YAML configuration file.
    """
    with open(filename, "r") as file:
        config = yaml.safe_load(file)
    return config

config_data = load_config()

# A tiny dummy comms implementation so the UI can run if the real serial port can't be opened.
class DummyComms:
    def __init__(self):
        self.name = "<dummy>"
    def sendCompact(self, msg):
        # no-op, log for debug
        print(f"[DummyComms] sendCompact called with: {msg}")
    def readCompact(self):
        # return empty lists so read_responses is a no-op
        return [], [], []
    def close(self):
        print("[DummyComms] close called")

def try_open_serial(port="COM3", baudrate=115200, retries=3, delay=1.0):
    """
    Try to construct SerialComms with retries. Return instance or None on failure.
    """
    for attempt in range(1, retries + 1):
        try:
            print(f"Attempt {attempt} opening serial port {port} (baud {baudrate})")
            ser = SerialComms.SerialComms(instrument="compact", port=port, baudrate=baudrate)
            print("Serial port opened:", getattr(ser, "name", repr(ser)))
            return ser
        except Exception as e:
            print(f"Attempt {attempt} failed to open {port}: {e}")
            traceback.print_exc()
            if attempt < retries:
                time.sleep(delay)
    return None

class YamlTestPage(QWidget):
    def __init__(self):
        super().__init__()
        global tabs

        # Diagnostics: list available ports
        ports = list(serial.tools.list_ports.comports())
        print("Available serial ports:")
        for p in ports:
            print("  ", p.device, "-", p.description, p.hwid)

        # Try to open serial comms with retries. If it fails, fall back to DummyComms so the UI remains usable.
        self.ser = try_open_serial(port="COM3", baudrate=115200, retries=3, delay=1.0)
        if self.ser is None:
            # Optionally show message box to the user
            print("WARNING: Could not open COM3. Running in offline/dummy mode.")
            # Provide the dummy comms so widgets that call sendCompact/readCompact won't crash.
            self.ser = DummyComms()

        # Left side (no scroll)
        left_widget = QWidget()
        left_layout = QVBoxLayout(left_widget)
        left_widget.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Fixed)  # Set vertical policy

        # Create the channels (system widgets)
        self.systemwidgets = []
        system = config_data.get('system', {})
        for channel, params in system.items():
            if not isinstance(params, dict):
                continue  # Skip malformed entries

            channel_type = params.get('type')
            if not channel_type:
                continue  # Skip if no type

            # Create an attribute on self with the name of the channel (lowercase)
            attr_name = channel.lower()

            if channel_type == 'Numeric':
                widget = ch.NumericMonitor(
                    name=params['name'],
                    group=params['group'],
                    COM=self.ser,
                    readback_command=params['read_command'],
                    description=params.get('description', ''),
                    units=params.get('units', ''),
                    conversion_factor=params.get('conversion_factor', '')
                )

            elif channel_type == 'Switch':
                widget = ch.SwitchSetting(
                    name=params['name'],
                    description=params.get('description', ''),
                    group=params['group'],
                    COM=self.ser,
                    get_command=params['read_command'],
                    set_command=params['write_command'],
                    options=params.get('options', ''),
                    default_value=params.get('default_value', '')
                )

            elif channel_type == 'Turbo':
                widget = ch.TurboSetting(
                    name=params['name'],
                    description=params.get('description', ''),
                    group=params['group'],
                    COM=self.ser,
                    readback_command=params['read_command'],
                    get_command=params.get('write_command'),
                    set_command=params.get('write_command'),
                )
            else:
                # Extend here for other types as you implement more classes
                continue

            setattr(self, attr_name, widget)
            self.systemwidgets.append(widget)
            print("Created widget:", attr_name, "widget.COM:", getattr(widget, "COM", None), "type:", type(getattr(widget, "COM", None)))

            # Add each widget's GUI to the layout
            for w in self.systemwidgets:
                left_layout.addWidget(w.gui)

        # Set up the window
        self.setWindowTitle("Bruker Control")
        central_widget = QWidget(self)
        central_widget.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Fixed)
        root = QHBoxLayout(central_widget)
        #root.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Fixed)

        # tabs
        tabs = QTabWidget()
        tabs.setSizePolicy(QSizePolicy.Preferred, QSizePolicy.Preferred)
        self._build_tabs()

        root.addWidget(left_widget, 0)              # Add left widget (no scroll)
        root.addWidget(tabs, 1)        # Add right scrollable area

        # If you want to set the layout of your central widget:
        self.setLayout(root)

        # Create a timer for periodically checking the pressures and turbos
        self.timer = QTimer(self)
        self.timer.setInterval(1000)
        self.timer.timeout.connect(self.monitor_loop)
        self.timer.start()

    def _build_tabs(self):
        # Helper to create a scrollable tab with its own widget+layout
        def make_scrollable_tab():
            area = QScrollArea()
            widget = QWidget()
            layout = QVBoxLayout(widget)
            widget.setLayout(layout)
            area.setWidget(widget)
            area.setWidgetResizable(True)
            return area, widget, layout

        # Create tabs + scroll areas
        self.SourceTab = QWidget()
        self.TransferTab = QWidget()
        self.QuadTabs = QWidget()
        self.CCTab = QWidget()
        self.TofTab = QWidget()

        src_area, src_widget, right_layout1 = make_scrollable_tab()
        trf_area, trf_widget, right_layout2 = make_scrollable_tab()
        quad_area, quad_widget, right_layout3 = make_scrollable_tab()
        cc_area, cc_widget, right_layout4 = make_scrollable_tab()
        tof_area, tof_widget, right_layout5 = make_scrollable_tab()

        # Put the scroll areas into the tab widgets (each tab gets its own layout)
        self.SourceTab.setLayout(QVBoxLayout())
        self.SourceTab.layout().addWidget(src_area)

        self.TransferTab.setLayout(QVBoxLayout())
        self.TransferTab.layout().addWidget(trf_area)

        self.QuadTabs.setLayout(QVBoxLayout())
        self.QuadTabs.layout().addWidget(quad_area)

        self.CCTab.setLayout(QVBoxLayout())
        self.CCTab.layout().addWidget(cc_area)

        self.TofTab.setLayout(QVBoxLayout())
        self.TofTab.layout().addWidget(tof_area)
        self.SourceTab.setSizePolicy(QSizePolicy.Minimum, QSizePolicy.Fixed)
        self.TransferTab.setSizePolicy(QSizePolicy.Minimum, QSizePolicy.Fixed)
        self.QuadTabs.setSizePolicy(QSizePolicy.Minimum, QSizePolicy.Fixed)
        self.CCTab.setSizePolicy(QSizePolicy.Minimum, QSizePolicy.Fixed)
        self.TofTab.setSizePolicy(QSizePolicy.Minimum, QSizePolicy.Fixed)

        # Create the channels lists
        self.channelwidgets = []
        self.sourcewidgets = []
        self.transferwidgets = []
        self.quadwidgets = []
        self.ccwidgets = []
        self.tofwidgets = []

        channels = config_data.get('channels', {})
        for channel, params in channels.items():
            if not isinstance(params, dict):
                continue
            channel_type = params.get('type')
            if not channel_type:
                continue

            attr_name = channel.lower()
            if channel_type == 'Numeric':
                widget = ch.NumericSettingWithReadback(
                    params['name'],
                    params.get('description', ''),
                    params['group'],
                    COM=self.ser,
                    readback_command=params['read_command'],
                    get_command=params['write_command'],
                    set_command=params['write_command'],
                    default_value=params.get('default_value'),
                    min_value=params.get('min_value'),
                    max_value=params.get('max_value'),
                    units=params.get('units', ''),
                    offset=params.get('offset', '')
                )
            elif channel_type == 'NumericNoReadback':
                widget = ch.NumericSettingNoReadback(
                    params['name'],
                    params.get('description', ''),
                    params['group'],
                    COM=self.ser,
                    get_command=params['read_command'],
                    set_command=params['write_command'],
                    default_value=params.get('default_value'),
                    min_value=params.get('min_value'),
                    max_value=params.get('max_value'),
                    units=params.get('units', ''),
                    offset=params.get('offset', '')
                )
            elif channel_type == 'Switch':
                widget = ch.SwitchSetting(
                    name=params['name'],
                    group=params['group'],
                    COM=self.ser,
                    get_command=params.get('read_command'),
                    set_command=params.get('write_command'),
                    description=params.get('description', ''),
                    options=params.get('options', ''),
                    default_value=params.get('default_value', ''),
                )
            else:
                continue

            setattr(self, attr_name, widget)
            self.channelwidgets.append(widget)
#             for widget in self.channelwidgets:
#                 widget.setFixedSize(QSize(200,100))

            group = params.get('group')
            if group == 'Source':
                self.sourcewidgets.append(widget)
                right_layout1.addWidget(widget.gui)
            elif group == 'Transfer':
                self.transferwidgets.append(widget)
                right_layout2.addWidget(widget.gui)
            elif group == 'Quad':
                self.quadwidgets.append(widget)
                right_layout3.addWidget(widget.gui)
            elif group == 'CC':
                self.ccwidgets.append(widget)
                right_layout4.addWidget(widget.gui)
            elif group == 'TOF':
                self.tofwidgets.append(widget)
                right_layout5.addWidget(widget.gui)
            else:
                continue

        tabs.addTab(self.SourceTab, "Source")
        tabs.addTab(self.TransferTab, "Transfer")
        tabs.addTab(self.QuadTabs, "Quad")
        tabs.addTab(self.CCTab, "CC")
        tabs.addTab(self.TofTab, "ToF")

        self.serial_lookup = {}
        #print(self.systemwidgets)
        #print(' ')
        #print(self.channelwidgets)
        for widget in self.systemwidgets + self.channelwidgets:
            if getattr(widget, "readback_command", None) is not None:
                for cmd in widget.readback_command.split(';'):
                    self.serial_lookup[cmd.rstrip('?').rstrip('=').rstrip('$')] = widget
            else:
                # guard in case widget.get_command is None
                getcmd = getattr(widget, "get_command", None)
                if getcmd:
                    self.serial_lookup[getcmd.rstrip('?').rstrip('=').rstrip('$')] = widget

    def monitor_loop(self):
        # Combine system and channel widgets
        all_widgets = self.systemwidgets + self.channelwidgets

        # Polling: try to request readbacks/get commands. If the comms are dummy, these will no-op.
        # To avoid flooding the serial, schedule read_responses via QTimer after issuing requests.
        for widget in all_widgets:
            try:
                if getattr(widget, "readback_command", None) is not None:
                    widget.readback()
                elif getattr(widget, "get_command", None) is not None:
                    widget.get()
            except Exception as e:
                # Defensive: if an individual widget errors while sending, log and continue
                print(f"Error when calling readback/get on widget {getattr(widget,'name',repr(widget))}: {e}")
                traceback.print_exc()
            #print(f'>> {widget.name}')
            time.sleep(.015)
            # Read responses a short time later (give the comms time to respond)
            #QTimer.singleShot(20, self.read_responses)
            self.read_responses()

    def read_responses(self):
        try:
            messages, values, responses = self.ser.readCompact()
        except Exception as e:
            print("Error calling readCompact on serial comms:", e)
            traceback.print_exc()
            return

        #print("read_responses: messages:", messages)
        for message, value, response in zip(messages, values, responses):
            #print('handling response:', response, 'from', message)
            if '?' in message:
                key = message.rstrip('?')
                if key in self.serial_lookup:
                    self.serial_lookup[key].updateReadback(message, value)
            elif '$' in message:
                key = message.rstrip('$')
                if key in self.serial_lookup:
                    self.serial_lookup[key].updateSetting(message, value)
            elif '=' in message:
                key = message.rstrip('=')
                if key in self.serial_lookup:
                    self.serial_lookup[key].updateSetting(message, value)

    def closeEvent(self, event):
        # Close serial comms if supported
        try:
            if hasattr(self.ser, "close"):
                self.ser.close()
        except Exception as e:
            print("Error closing serial comms:", e)
            traceback.print_exc()
        event.accept()