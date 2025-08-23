
from PyQt5.QtCore import QObject, pyqtSignal, QThread, QTimer
from serial.tools import list_ports
import serial
from time import sleep
from instrument_app.util.parsing import parse_arduino_line, Reading
from instrument_app.config.settings import BAUD_RATE, READ_PERIOD_MS

class SerialWorker(QObject):
    reading = pyqtSignal(object)  # Reading
    status  = pyqtSignal(str)
    def __init__(self, port, baud):
        super().__init__()
        self._port, self._baud = port, baud
        self._ser = None
        self._timer = QTimer()
        self._timer.timeout.connect(self._poll_once)

    def start(self):
        try:
            self._ser = serial.Serial(self._port, self._baud, timeout=2)
            sleep(1.2)
            self._ser.reset_input_buffer()
            self.status.emit(f"Connected {self._port}")
            self._timer.start(READ_PERIOD_MS)
        except Exception as e:
            self.status.emit(f"Open error: {e}")

    def stop(self):
        self._timer.stop()
        try:
            if self._ser: 
               self._ser.close()
        finally:
            self._ser = None
            self.status.emit("Disconnected")

    def _poll_once(self):
        if not self._ser:
            return
        try:
            raw = self._ser.readline().decode(errors="replace")
            r = parse_arduino_line(raw)
            if r: 
                self.reading.emit(r)
        except Exception as e:
            self.status.emit(f"Serial error: {e}")

class SerialManager(QObject):
    connectedChanged = pyqtSignal(bool, str)
    reading = pyqtSignal(object)
    status  = pyqtSignal(str)

    def __init__(self):
        super().__init__()
        self._thread = None
        self._worker = None

    @staticmethod
    def available_ports():
        return list(list_ports.comports())

    def connect(self, port: str):
        self.disconnect()
        self._thread = QThread()
        self._worker = SerialWorker(port, BAUD_RATE)
        self._worker.moveToThread(self._thread)
        self._thread.started.connect(self._worker.start)
        self._worker.reading.connect(self.reading)
        self._worker.status.connect(self.status)
        self._thread.start()
        self.connectedChanged.emit(True, port)

    def disconnect(self):
        if self._worker:
            self._worker.stop()
        if self._thread:
            self._thread.quit()
            self._thread.wait()
        self._thread = None
        self._worker = None
        self.connectedChanged.emit(False, "Disconnected")
