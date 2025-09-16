'''
Built from Chris's code
'''


from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout,
)
from PyQt5.QtCore import QTimer
from instrument_app.util import SerialComms
import instrument_app.widgets.Channels as ch

class BrukerControlPage(QWidget): 
    def __init__(self):
            super().__init__()

            # Set up serial comms
            self.ser = SerialComms.SerialComms(instrument = "compact", port = "COM1", baudrate = 115200)

            # Set up the window
            self.setWindowTitle("Vacuum Monitor")
            central_widget = QWidget(self)
            layout = QVBoxLayout(central_widget)

            # Create the channels
            self.FLpressure = ch.NumericMonitor("FL Pressure", "Vacuum", self.ser, "VACU:SRPV", "Foreline Pressure", "Torr", (0.76,0))
            self.TOFpressure = ch.NumericMonitor("TOF Pressure", "Vacuum", self.ser, "VACU:SMPV", "TOF Pressure", "Torr", (0.76,0))
            self.TP1 = ch.TurboSetting("TP1", "Vacuum", self.ser, "TP_1:MOSW?;TP_1:ROTR?;TP_1:POWR", "TP_1:MOSW", "Source TP")
            self.TP2 = ch.TurboSetting("TP2", "Vacuum", self.ser, "TP_2:MOSW?;TP_2:ROTR?;TP_2:POWR", "TP_2:MOSW", "TOF TP")
            self.V1 = ch.NumericSetting("V1", "Voltages", self.ser, "FOC1:L2V_", "FOC1:L2V_", 10, -40, 40, units="V", description="FOC1:L2V")
            self.V2 = ch.NumericSetting("V2", "Voltages", self.ser, "FUN1:RFA_", "FUN1:RFA_",  20, 0, 100, units="V", description="FUN1:RFA")
            self.mode = ch.SwitchSetting("Mode", "Instrument", self.ser, "CTRL:MODE", options=["Shutdown","Standby Instrument","Standby","Operate","Acquisition","Mystery Mode 5","Mystery Mode 6"], default_value="Standby")

            # Add each channel's widget to the layout of the main window
            layout.addWidget(self.FLpressure.gui)
            layout.addWidget(self.TOFpressure.gui)
            layout.addWidget(self.TP1.gui)
            layout.addWidget(self.TP2.gui)
            layout.addWidget(self.V1.gui)
            layout.addWidget(self.V2.gui)
            layout.addWidget(self.mode.gui)
            self.setCentralWidget(central_widget)

            # Create a timer for periodically checking the pressures and turbos
            self.timer = QTimer(self)
            self.timer.setInterval(1000)
            self.timer.timeout.connect(self.monitor_loop)
            self.timer.start()

    def monitor_loop(self):
            # Read the pressures and turbo properties
            self.FLpressure.readActual()
            self.TOFpressure.readActual()
            self.TP1.readActual()
            self.TP2.readActual()
            self.V1.readActual()
            self.V2.readActual()

    def closeEvent(self, event):
                self.timer.stop()
                self.ser.close()
                event.accept()

