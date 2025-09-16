import serial
import time

class SerialComms():
    def __init__(self, instrument="Compact", port = 'COM1', baudrate=115200, timeout=10):

        self.instrument = instrument
        self.ser = serial.Serial(port = port, baudrate=baudrate, timeout=timeout)
    
    def close(self):
        self.ser.close()

    def getMessageCompact(self, message):
        message_bytes = bytes(message, 'ascii')
        checksum = str(hex(self.crc16(message_bytes, 0, len(message_bytes)))).upper()
        message = message + "@" + checksum[2:] + "\r"
        return message

    def sendCompact(self, message):
        message_bytes = bytes(message, 'ascii')
        message_list = message[0:-6].strip('\r').split(';')
        checksum = str(hex(self.crc16(message_bytes, 0, len(message_bytes)))).upper()
        message = message + "@" + checksum[2:] + "\r"
        message_bytes = bytes(message, 'ascii')
        self.ser.write(message_bytes)
        time.sleep(.015)
        if self.ser.in_waiting > 0:
            data = self.ser.read(self.ser.in_waiting)
            data = data.replace(b'\x00',b'').replace(b'\x06', b'').strip(b'\r').split(b'\r')
            data = [d.decode('ascii') for d in data]
            results = []
            responses = []
            for m, d in zip(message_list, data):
                if m in d:
                    response, checksum = d.split("@")
                    checkchecksum = str(hex(self.crc16(bytes(response, 'ascii'), 0, len(response))))[2:].upper()
                    while len(checkchecksum) < 4:
                        checkchecksum = "0" + checkchecksum
                    if checksum == checkchecksum:
                        if "?" in response:
                            results.append(response.split("?")[-1])
                            responses.append(response)
                        elif "=" in response:
                            results.append(response.split("=")[-1])
                            responses.append(response)
                    else:
                        print("Checksum wrong")
                        return None
        else:
            print("No response to command")
            return None
        if len(results) > 0:
            return results, responses
        else:
            print("Response empty")
            return None, None
        
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
    #message = ser.getMessageCompact('QP_1:RFA_?')
    message = ser.getMessageCompact('TP_1:MOSW?;TP_1:ROTR?;TP_1:POWR?')
    print(ser.sendCompact(message))


    
    ser.close()