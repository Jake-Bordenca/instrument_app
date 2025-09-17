import yaml
import instrument_app.widgets.Channels as ch
from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout,
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
            layout = QVBoxLayout(central_widget)

            # Create the channels
            widgets = [] 
            for ch_type, ch_params in config_data.items():
                for channel, params in ch_params.items():
                    if isinstance(params, dict): 
                        if params['type']== 'Numeric':
                            self.params['name'] = ch.NumericSetting(params['name'], params['group'], self.ser, params['read_command'],params['write_command'],params['default_value'],params['min_value'],params['max_value'],units=params['units'], description=params['description'],)
                            widgets.append(self.params['name'])                        
                        else:
                            pass
                    else:
                        pass    

            # Add each channel's widget to the layout of the main window
            for i in range(len(widgets)):
                layout.addWidget(self.params['name'].gui)
            #self.setCentralWidget(central_widget)

    def closeEvent(self, event):
                self.ser.close()
                event.accept()

#self.V1 = ch.NumericSetting("V1", "Voltages", self.ser, "FOC1:L2V_", "FOC1:L2V_", 10, -40, 40, units="V", description="FOC1:L2V")