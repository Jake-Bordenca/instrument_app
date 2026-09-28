import time

import serial
import serial.tools.list_ports
from PyQt5.QtCore import QObject, QTimer


class ArduinoSerialComms(QObject):
    def __init__(self, channels=None, baudrate=115200, timeout=0.1, poll_interval_ms=100, parent=None):
        super().__init__(parent)
        self.channels = channels
        self.baudrate = baudrate
        self.timeout = timeout
        self.poll_interval_ms = poll_interval_ms
        self._serial = None
        self._timer = QTimer(self)
        self._timer.timeout.connect(self._read_serial)

    def refresh_ports(self):
        ports = serial.tools.list_ports.comports()
        return [f"{port.device} ({port.description})" for port in ports]

    def open_port(self, port_name):
        if self._serial:
            return
        try:
            # Add debug logging
            import traceback
            with open('serial_debug.log', 'a') as f:
                f.write(f"Attempting to open {port_name} at {self.baudrate} baud\n")

            # Open serial port with DTR disabled to prevent Arduino reset
            self._serial = serial.Serial()
            self._serial.port = port_name
            self._serial.baudrate = self.baudrate
            self._serial.timeout = self.timeout
            self._serial.dtr = False  # Disable DTR to prevent Arduino reset
            self._serial.open()

            with open('serial_debug.log', 'a') as f:
                f.write(f"Serial port opened successfully (DTR disabled)\n")

            # Wait for Arduino to be ready (in case it did reset)
            time.sleep(2.0)

            # Clear any buffered data from Arduino startup messages
            if self._serial.in_waiting:
                self._serial.read(self._serial.in_waiting)
                with open('serial_debug.log', 'a') as f:
                    f.write(f"Cleared {self._serial.in_waiting} bytes of startup buffer\n")

            self._timer.start(self.poll_interval_ms)
            if self.channels:
                self.channels.connection_changed.emit(True, port_name)

            # Request current state from Arduino after connection
            time.sleep(0.1)
            self._serial.write(b'?')  # Send status query

            with open('serial_debug.log', 'a') as f:
                f.write(f"Connection established, state query sent\n")
        except Exception as exc:
            import traceback
            with open('serial_debug.log', 'a') as f:
                f.write(f"ERROR: {exc}\n")
                f.write(traceback.format_exc())
            if self.channels:
                self.channels.error.emit(f"Serial open failed: {exc}")
            self._serial = None

    def close_port(self):
        if not self._serial:
            return
        self._timer.stop()
        try:
            self._serial.close()
        finally:
            self._serial = None
            if self.channels:
                self.channels.connection_changed.emit(False, "")

    def send_command(self, cmd):
        if not self._serial:
            if self.channels:
                self.channels.error.emit("Not connected to Arduino")
            return
        try:
            self._serial.write(cmd.encode())
            if self.channels:
                self.channels.command_sent.emit(cmd)
        except Exception as exc:
            if self.channels:
                self.channels.error.emit(f"Error sending command: {exc}")

    def _read_serial(self):
        if not self._serial:
            return
        try:
            # Check if port is still open
            if not self._serial.is_open:
                if self.channels:
                    self.channels.error.emit("Serial port closed unexpectedly")
                self.close_port()
                return

            if not self._serial.in_waiting:
                return

            line = self._serial.readline().decode('utf-8', errors='ignore').strip()
        except (OSError, IOError) as exc:
            # Port disconnected or hardware error
            if self.channels:
                self.channels.error.emit(f"Serial port error: {exc}")
            self.close_port()
            return
        except Exception as exc:
            if self.channels:
                self.channels.error.emit(f"Serial read error: {exc}")
            return

        # Debug: log all received lines
        with open('serial_debug.log', 'a') as f:
            f.write(f"RAW: {line}\n")
        faultmsg = {}
        # Data lines always start with "ms: "; skip everything else (banner, help, header)
        if not line.startswith('ms: '):
            return

        parsed = self._parse_line(line)

        # Debug: log parsing result
        with open('serial_debug.log', 'a') as f:
            f.write(f"PARSED: {parsed}\n")

        if parsed and self.channels:
            self.channels.data_received.emit(parsed)

    @staticmethod
    def _parse_line(line):
        data = {}
        for part in line.split(','):
            part = part.strip()
            if ':' not in part:
                continue
            key, _, val = part.partition(':')
            data[key.strip()] = val.strip()

        required = {
            'ms', 'uhvTorr_A', 'uhvTorr_B', 'foreTorr_A', 'foreTorr_B',
            'stateA', 'stateB', 'tv850iA_ok', 'tv850iB_ok', 'tv350iA_ok', 'tv350iB_ok',
            'rel_tv850iA', 'rel_tv850iB', 'rel_tv350iA', 'rel_tv350iB',
            'rel_hornetA', 'rel_hornetB',
            'fault_hornetA', 'fault_systemA', 'fault_hornetB', 'fault_systemB', 'maint',
        }
        if not required.issubset(data.keys()):
            return None

        try:
            return {
                "timestamp_ms": int(data['ms']),
                "uhv_torr_a":   float(data['uhvTorr_A']),
                "uhv_torr_b":   float(data['uhvTorr_B']),
                "fore_torr_a":  float(data['foreTorr_A']),
                "fore_torr_b":  float(data['foreTorr_B']),
                "state_a":      data['stateA'],
                "state_b":      data['stateB'],
                "tv850ia_ok":   data['tv850iA_ok'],
                "tv850ib_ok":   data['tv850iB_ok'],
                "tv350ia_ok":   data['tv350iA_ok'],
                "tv350ib_ok":   data['tv350iB_ok'],
                "rel_tv850ia":  int(data['rel_tv850iA']),
                "rel_tv850ib":  int(data['rel_tv850iB']),
                "rel_tv350ia":  int(data['rel_tv350iA']),
                "rel_tv350ib":  int(data['rel_tv350iB']),
                "rel_hornet_a": int(data['rel_hornetA']),
                "rel_hornet_b": int(data['rel_hornetB']),
                "fault_hornet_a": int(data['fault_hornetA']),
                "fault_system_a": int(data['fault_systemA']),
                "fault_hornet_b": int(data['fault_hornetB']),
                "fault_system_b": int(data['fault_systemB']),
                "maint":        int(data['maint']),
            }
        except (ValueError, KeyError):
            return None

class SerialComms():
    def __init__(self, instrument="Compact", port = 'COM3', baudrate=115200, timeout=10):
        self.instrument = instrument
        self.ser = serial.Serial(port = port, baudrate=baudrate, timeout=timeout)
        self.queue = {}
    

    def close(self):
        self.ser.close()


    def getMessageCompact(self, message):
        message_bytes = bytes(message, 'ascii')
        checksum = str(hex(self.crc16(message_bytes, 0, len(message_bytes)))).upper()
        message = message + "@" + checksum[2:] + "\r"
        return message


    def sendCompact(self, message):
        message_bytes = bytes(message, 'ascii')
        message_list = message.strip('\r').split(';')
        checksum = str(hex(self.crc16(message_bytes, 0, len(message_bytes)))).upper()[2:]
        while len(checksum) < 4:
                checksum = "0" + checksum
        message = message + "@" + checksum + "\r"
        message_bytes = bytes(message, 'ascii')
        if '=' in message:
            print(message)
        self.ser.write(message_bytes)
        #print('>>', message)
        for m in message_list:
            if '=' in m:
                m = m.split('=')[0] + '='
            #print("add", m)
            if m in self.queue.keys():
                print(f'Missed a response for {m}')
            self.queue[m] = time.perf_counter()


    def readCompact(self):
        messages, values, responses = [], [], []
        while self.ser.in_waiting > 0:
            data = self.ser.read_until(b'\r')
            data = data.replace(b'\x00',b'').replace(b'\x06', b'').strip(b'\r').decode('ascii')
            if "@" not in data:
                continue
            #print('<<', data)
            response, checksum = data.split("@")
            check_checksum = str(hex(self.crc16(bytes(response, 'ascii'), 0, len(response))))[2:].upper()
            while len(check_checksum) < 4:
                check_checksum = "0" + check_checksum
            if checksum == check_checksum:
                if "!ERR" in response:
                    print(response)
                elif "?" in response:
                    message, value = response.split("?")
                    message = message + "?"
                    messages.append(message)
                    values.append(value)
                    responses.append(response)
                elif "=" in response:
                    print(response)
                    message, value = response.split("=")
                    message = message + "="
                    messages.append(message)
                    values.append(value)
                    responses.append(response)
                elif "$" in response:
                    message, value = response.split("$")
                    message = message + "$"
                    messages.append(message)
                    values.append(value)
                    responses.append(response)
                else:
                    print("Unexpected response format received:", response, 'from message:', message)
                    break
            else:
                print("Checksum wrong")
                break
            if message in self.queue.keys():
                del self.queue[message]
            else:
                print(f"No corresponding message for {message} found in queue")

        return messages, values, responses
        
    
    def purgeQueue(self):
        current_time = time.perf_counter()
        for message, send_time in self.queue.items():
            if current_time - send_time > 1000:
                print('Purging', message)
                del self.queue[message]


    @staticmethod
    def crc16(data : bytearray, offset , length):
        if data is None or offset < 0 or offset > len(data)- 1 and offset+length > len(data):
            return 0
        crc = 0xFFFF
        for i in range(0, length):
            crc ^= data[offset + i] << 8
            for j in range(0,8):
                if (crc & 0x8000) > 0:
                    crc =(crc << 1) ^ 0x1021
                else:
                    crc = crc << 1
        return crc & 0xFFFF


if __name__ == '__main__':
    ser = SerialComms()
    
    message = ser.getMessageCompact('TP_1:MOSW?;TP_1:ROTR?;TP_1:POWR?')
    print(ser.sendCompact(message))

    ser.close()