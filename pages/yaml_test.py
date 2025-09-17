import yaml
import instrument_app.widgets.Channels as ch
from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout,
)
from PyQt5.QtCore import QTimer
from instrument_app.util import SerialComms

def load_config(filename="config\setup_Compact.yaml"):
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
            root= QHBoxLayout(central_widget)
            left= QVBoxLayout()
            right= QVBoxLayout()
            root.addLayout(left, 0); root.addLayout(right, 1)

            # Create the channels
            channelwidgets = [] 
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
                            params.get('description', ''),
                            params['group'],
                            self.ser,
                            params['read_command'],
                            params['write_command'],
                            params['options'],
                            params['default_value'],
                        )
                    else:
                        # Extend here for other types as you implement more classes
                        continue

                    setattr(self, attr_name, widget)
                    channelwidgets.append(widget)

                    # Add each widget's GUI to the layout
                    for widget in channelwidgets:
                        left.addWidget(widget.gui)
                    #self.setCentralWidget(central_widget)
            
             # Create the channels
            systemwidgets = [] 
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
                        widget = ch.NumericSetting(
                            params['name'],
                            params['group'],
                            self.ser,
                            params['read_command'],
                            params.get('write_command', ''),
                            params.get('description', ''),
                            params.get('default_value', 0),
                            params.get('min_value', 0),
                            params.get('max_value', 0),
                            units=params.get('units', '')
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
                        widget = ch.SwitchSetting(
                            params['name'],
                            params.get('description', ''),
                            params['group'],
                            self.ser,
                            params['read_command'],
                            params['write_command'],
                        )
                    else:
                        # Extend here for other types as you implement more classes
                        continue

                    setattr(self, attr_name, widget)
                    systemwidgets.append(widget)

                    # Add each widget's GUI to the layout
                    for widget in systemwidgets:
                        right.addWidget(widget.gui)          
          

    def closeEvent(self, event):
                self.ser.close()
                event.accept()
