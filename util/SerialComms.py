import serial
import time

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
        checksum = str(hex(self.crc16(message_bytes, 0, len(message_bytes)))).upper()
        message = message + "@" + checksum[2:] + "\r"
        message_bytes = bytes(message, 'ascii')
        self.ser.write(message_bytes)
        for m in message_list:
            if '=' in m:
                m = m.split('=')[0] + '='
            #print("add", m)
            self.queue[m] = time.perf_counter()


    def readCompact(self):
        messages, values, responses = [], [], []
        while self.ser.in_waiting > 0:
            data = self.ser.read_until(b'\r')
            data = data.replace(b'\x00',b'').replace(b'\x06', b'').strip(b'\r').decode('ascii')
            if "@" not in data:
                continue
            response, checksum = data.split("@")
            check_checksum = str(hex(self.crc16(bytes(response, 'ascii'), 0, len(response))))[2:].upper()
            while len(check_checksum) < 4:
                check_checksum = "0" + check_checksum
            if checksum == check_checksum:
                if "?" in response:
                    message, value = response.split("?")
                    message = message + "?"
                    messages.append(message)
                    values.append(value)
                    responses.append(response)
                elif "=" in response:
                    message, value = response.split("=")
                    message = message + "="
                    messages.append(message)
                    values.append(value)
                    responses.append(response)
                else:
                    print("Unexpected response format received:", response)
                    break
            else:
                print("Checksum wrong")
                break

            del self.queue[message]

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