import serial
import sys
import time
import threading

DMX_BAUD = 250000

DMX_START_CODE = 0x00
DMX_BREAK_LENGTH = 100
DMX_MARK_LENGTH = 15

MICROSECONDS = 1000000

class DMX(object):
    
    def __init__(self, port):
        self.dmx_frame = [0]*512
        self._ser = serial.Serial(port, baudrate=DMX_BAUD, stopbits=2)
        self._thr = threading.Thread(target=self._send, daemon=True)

    def start_thread(self):
        self._thr.start()
    
    def _send(self):
        while True:
            self.send_frame(self.dmx_frame)

    def send_frame(self, frame):
        self._ser.sendBreak(DMX_BREAK_LENGTH/MICROSECONDS)
        time.sleep(DMX_MARK_LENGTH/MICROSECONDS)
        assert len(frame) == 512
        self._ser.write(bytes([0x00]+frame))
        
