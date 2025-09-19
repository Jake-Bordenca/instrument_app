import yaml
import instrument_app.widgets.Channels as ch
from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QScrollArea, QSizePolicy
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
            self.setWindowTitle("Vacuum Monitor")
            central_widget = QWidget(self)
            root = QHBoxLayout(central_widget)

            # Left side (no scroll)
            left_widget = QWidget()
            left_layout = QVBoxLayout(left_widget)
            left_widget.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Fixed)  # Set vertical policy

            # Right scroll area setup
            right_scroll_area = QScrollArea()
            right_scroll_widget = QWidget()
            right_scroll_widget.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Fixed)  # Set vertical policy
            right_layout = QVBoxLayout(right_scroll_widget)
            right_scroll_area.setWidget(right_scroll_widget)
            right_scroll_area.setWidgetResizable(True)

            root.addWidget(left_widget, 0)              # Add left widget (no scroll)
            root.addWidget(right_scroll_area, 1)        # Add right scrollable area

            # If you want to set the layout of your central widget:
            self.setLayout(root)


             # Create the channels
            self.channelwidgets = [] 
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

                    # Add each widget's GUI to the layout
                    for widget in self.channelwidgets:
                        right_layout.addWidget(widget.gui)
                    #self.setCentralWidget(central_widget) 
            
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