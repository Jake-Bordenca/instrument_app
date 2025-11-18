import yaml
import instrument_app.widgets.Channels as ch
from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QScrollArea, QSizePolicy, QTabWidget
)
from PyQt5.QtCore import QTimer
from instrument_app.util import SerialComms

def load_config(filename="instrument_app\config\setup_Compact.yaml"):
    """
    Loads a YAML configuration file.
    """
    with open(filename, "r") as file:
        config = yaml.safe_load(file)
    return config

config_data = load_config()

class YamlTestPage(QWidget): 
    def __init__(self):
            super().__init__()

            # Set up serial comms
            self.ser = SerialComms.SerialComms(instrument = "compact", port = "COM3", baudrate = 115200)

            # Set up the window
            self.setWindowTitle("Bruker Control")
            central_widget = QWidget(self)
            root = QHBoxLayout(central_widget)

            # Left side (no scroll)
            left_widget = QWidget()
            left_layout = QVBoxLayout(left_widget)
            left_widget.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Fixed)  # Set vertical policy

            root.addWidget(left_widget, 0)              # Add left widget (no scroll)
            root.addWidget(self.tabs, 1)        # Add right scrollable area

                    # tabs         
            self.tabs = QTabWidget()
            self._build_tabs()

            # If you want to set the layout of your central widget:
            self.setLayout(root)

             # Create the channels
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
                            params['name'],
                            params['group'],
                            self.ser,
                            params['read_command'],
                            params.get('description', ''),
                            params.get('units', ''),
                            params.get('conversion_factor' , '')
                        )

                    elif channel_type == 'Switch':
                        widget = ch.SwitchSetting(
                            params['name'],
                            params.get('description', ''),
                            params['group'],
                            self.ser,
                            params['read_command'],
                            params['write_command'],
                            params['options'],
                            params['default_value'],
                        )

                    elif channel_type == 'Turbo':
                        widget = ch.TurboSetting(
                            params['name'],
                            params['group'],
                            self.ser,
                            params['read_command'],
                            params['write_command'],
                            params.get('description', ''),
                        )
                    else:
                        # Extend here for other types as you implement more classes
                        continue

                    setattr(self, attr_name, widget)
                    self.systemwidgets.append(widget)

                    # Add each widget's GUI to the layout
                    for widget in self.systemwidgets:
                        left_layout.addWidget(widget.gui)          
          
            # Create a timer for periodically checking the pressures and turbos
            self.timer = QTimer(self)
            self.timer.setInterval(1000)
            self.timer.timeout.connect(self.monitor_loop)
            self.timer.start()

    def _build_tabs(self):
        # Right scroll area setup

        right_scroll_area = QScrollArea()
        right_scroll_widget = QWidget()
        right_scroll_widget.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Fixed)  # Set vertical policy
        right_layout = QVBoxLayout(right_scroll_widget)
        right_scroll_area.setWidget(right_scroll_widget)
        right_scroll_area.setWidgetResizable(True)

        self.SourceTab = QWidget()
        self.TransferTab = QWidget()
        self.QuadTabs = QWidget()
        self.CCTab = QWidget()
        self.TofTab = QWidget()

        self.SourceTab.setLayout(right_layout)
        self.TransferTab.setLayout(right_layout)
        self.QuadTabs.setLayout(right_layout)
        self.CCTab.setLayout(right_layout)
        self.TofTab.setLayout(right_layout)

        # Create the channels
        self.channelwidgets = []
        self.sourcewidgets = []
        self.transferwidgets = []
        self.quadwidgets = []
        self.ccwidgets = []
        self.tofwidgets = [] 

        channels = config_data.get('channels', {})
        for channel, params in channels.items():
                if not isinstance(params, dict):
                    continue  # Skip malformed entries

                channel_type = params.get('type')
                if not channel_type:
                    continue  # Skip if no type

        # Create an attribute on self with the name of the channel (lowercase)
                attr_name = channel.lower()

                if channel_type == 'Numeric':
                    widget = ch.NumericSetting(
                        params['name'],
                        params['group'],
                        self.ser,
                        params['read_command'],
                        params['write_command'],
                        params.get('description', ''),
                        params['default_value'],
                        params['min_value'],
                        params['max_value'],
                        units=params.get('units', ''),
                    )
                elif channel_type == 'Switch':
                    widget = ch.SwitchSetting(
                        params['name'],
                        params['group'],
                        self.ser,
                        set_command= params['read_command'],
                        description = params.get('description', ''),
                        options = params.get('options', ''),
                        default_value = params.get('default_value', ''),
                    )
                else:
                    continue 

                setattr(self, attr_name, widget)
                self.channelwidgets.append(widget)

                for widget in self.channelwidgets:
                    if params.get('group') == 'Source':
                        self.sourcewidgets.append(widget)
                        self.SourceTab.layout().addWidget(widget.gui)
                    elif params.get('group') == 'Transfer':
                        self.transferwidgets.append(widget)
                        self.TransferTab.layout().addWidget(widget.gui)
                    elif params.get('group') == 'Quad':
                        self.quadwidgets.append(widget)
                        self.QuadTabs.layout().addWidget(widget.gui)
                    elif params.get('group') == 'CC':
                        self.ccwidgets.append(widget)
                        self.CCTab.layout().addWidget(widget.gui)
                    elif params.get('group') == 'ToF':
                        self.tofwidgets.append(widget)
                        self.TofTab.layout().addWidget(widget.gui)
                    else:
                        continue    
                # Add each widget's GUI to the layout
                #for widget in self.channelwidgets:
                #     right_layout.addWidget(widget.gui)

        self.tabs.addTab(self.SourceTab, "Source")
        self.tabs.addTab(self.TransferTab, "Transfer")
        self.tabs.addTab(self.QuadTabs, "Quad")
        self.tabs.addTab(self.CCTab, "CC")
        self.tabs.addTab(self.TofTab, "ToF")

    def monitor_loop(self):
    # Combine all widgets into a single list
        all_widgets = self.systemwidgets + self.channelwidgets
        for widget in all_widgets:
            if isinstance(widget, ch.NumericSetting) or isinstance(widget, ch.NumericMonitor) or isinstance(widget, ch.TurboSetting):
                widget.readActual()
            elif isinstance(widget, ch.SwitchSetting):
                pass
                #widget.readSetting()
        print('Finished one monitor loop')

    def closeEvent(self, event):
                self.ser.close()
                event.accept()