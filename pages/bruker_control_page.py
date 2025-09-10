'''
Built from Chris's code
'''


from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QGridLayout, QGroupBox, QFormLayout,
    QLabel, QPushButton, QDoubleSpinBox, QSpinBox, QCheckBox, QTableWidget,
    QTableWidgetItem, QHeaderView, QSplitter, QComboBox, QMessageBox, QMainWindow
)
from PyQt5.QtCore import QTimer
import sys
from instrument_app.util import SerialComms
from instrument_app.widgets.pressuremonitor import QPressureMonitor
from instrument_app.widgets.turbocontrol import QTurboControl
from instrument_app.widgets.voltagecontrol import QVoltageControl

class BrukerControlPage(QWidget): 
    def __init__(self):
                super().__init__()

                self.setWindowTitle("Test")
                central_widget = QWidget(self)
                layout = QVBoxLayout(central_widget)

                self.FLpressure = QPressureMonitor("FL Pressure", "VACU:SRPV", "Torr")
                self.TOFpressure = QPressureMonitor("TOF Pressure", "VACU:SMPV", "Torr")
                self.TP1 = QTurboControl("TP1", "TP_1")
                self.TP2 = QTurboControl("TP2", "TP_2")
                self.V1 = QVoltageControl("FOC1 L2V", "FOC1:L2V_", "FOC1:L2V_", 10, 0, 400, units="V")
                self.V2 = QVoltageControl("FUN1 RFA", "FUN1:RFA_", "FUN1:RFA_", 20, 0, 400, units="V")
                layout.addWidget(self.FLpressure)
                layout.addWidget(self.TOFpressure)
                layout.addWidget(self.TP1)
                layout.addWidget(self.TP2)
                layout.addWidget(self.V1)
                layout.addWidget(self.V2)
                #self.setCentralWidget(central_widget)

                self.timer = QTimer(self)
                self.timer.setInterval(1000)
                self.timer.timeout.connect(self.loop_iteration)
                self.ser = SerialComms.SerialComms()
                self.timer.start()

    def loop_iteration(self):
                
                message = self.ser.getMessageCompact(self.TOFpressure.get_update_message())
                response = self.ser.sendCompact(message)
                self.TOFpressure.update(response)
                message = self.ser.getMessageCompact(self.FLpressure.get_update_message())
                response = self.ser.sendCompact(message)
                self.FLpressure.update(response)
                message = self.ser.getMessageCompact(self.TP1.get_update_message())
                response = self.ser.sendCompact(message)
                self.TP1.update(response)
                message = self.ser.getMessageCompact(self.TP2.get_update_message())
                response = self.ser.sendCompact(message)
                self.TP2.update(response)
                message = self.ser.getMessageCompact(self.V1.get_readback_message())
                response = self.ser.sendCompact(message)
                self.V1.update_readback(response)
                message = self.ser.getMessageCompact(self.V1.get_readback_message())
                response = self.ser.sendCompact(message)
                self.V1.update_readback(response)
                message = self.ser.getMessageCompact(self.V2.get_readback_message())
                response = self.ser.sendCompact(message)
                self.V2.update_readback(response)
                message = self.ser.getMessageCompact(self.V2.get_readback_message())
                response = self.ser.sendCompact(message)
                self.V2.update_readback(response)

    def closeEvent(self, event):
                self.timer.stop()
                self.ser.close()
                event.accept()
'''
      class MainWindow(QMainWindow):
       def __init__(self):
                super().__init__()

                self.setWindowTitle("Test")
                central_widget = QWidget(self)
                layout = QVBoxLayout(central_widget)

                self.V1 = QVoltageControl("V1", "V1:Write", "V1:Read", 10, 0, 100, units="V")
                self.V2 = QVoltageControl("V2", "V2:Write", "V2:Read", 20, 0, 100, units="us")

                
                self.setCentralWidget(central_widget)
                self.setLayout(layout)

       def closeEvent(self, event):
                event.accept()
    elif testnumber == 2:
      class MainWindow(QMainWindow):
       def __init__(self):
                super().__init__()

                self.setWindowTitle("Test Voltage Setting and Readback")
                central_widget = QWidget(self)
                layout = QVBoxLayout(central_widget)



                layout.addWidget(self.V1)
                layout.addWidget(self.V2)
                self.setCentralWidget(central_widget)
                self.setLayout(layout)

                self.timer = QTimer(self)
                self.timer.setInterval(1000)
                self.timer.timeout.connect(self.loop_iteration)
                self.ser = SerialComms.SerialComms()
                self.timer.start()

       def loop_iteration(self):
                
                message = self.ser.getMessageCompact(self.V1.get_readback_message())
                response = self.ser.sendCompact(message)
                self.V1.update_readback(response)
                message = self.ser.getMessageCompact(self.V1.get_readback_message())
                response = self.ser.sendCompact(message)
                self.V1.update_readback(response)
                message = self.ser.getMessageCompact(self.V2.get_readback_message())
                response = self.ser.sendCompact(message)
                self.V2.update_readback(response)
                message = self.ser.getMessageCompact(self.V2.get_readback_message())
                response = self.ser.sendCompact(message)
                self.V2.update_readback(response)

            #def set_message(self, message):


       def closeEvent(self, event):
                self.timer.stop()
                self.ser.close()
                event.accept()
'''