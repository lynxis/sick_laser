#!/usr/bin/env python2

import logging
from serial import Serial
import crc16
from struct import pack, unpack

LOG = logging.getLogger('laser')
MAX_TELEGRAMM_LENGTH = 1024

class TelegrammError(RuntimeError):
    pass

class DeviceStatusInvalidForWrites(TelegrammError):
    _errorcode = 0x1

class AccessNotAllowed(TelegrammError):
    _errorcode = 0x2

class PasswordIncorrect(TelegrammError):
    _errorcode = 0x3

class TokenAlreadyTaken(TelegrammError):
    _errorcode = 0x4

class InvalidArguement(TelegrammError):
    _errorcode = 0x5

class DeviceBusyOrInternalError(TelegrammError):
    _errorcode = 0x6

class AccessNotSupported(TelegrammError):
    _errorcode = 0x7

class CommunicationError(TelegrammError):
    _errorcode = 0xa

class AddressInvalid(TelegrammError):
    _errorcode = 0xc

class TelegramIdInvalid(TelegrammError):
    _errorcode = 0x10

class BlockNumberInvalid(TelegrammError):
    _errorcode = 0x14

class CommandTypeInvalid(TelegrammError):
    _errorcode = 0x16

class TelegrammFormatError(TelegrammError):
    _errorcode = 0x34

class CommandTelegramError(TelegrammError):
    _errorcode = 0x36

class UnknownTelegramError(TelegrammError):
    _errorcode = 0xff

_ERRORS = {
    0x1: DeviceStatusInvalidForWrites,
    0x2: AccessNotAllowed,
    0x3: PasswordIncorrect,
    0x4: TokenAlreadyTaken,
    0x5: InvalidArguement,
    0x6: DeviceBusyOrInternalError,
    0x7: AccessNotSupported,
    0xa: CommunicationError,
    0xc: AddressInvalid,
    0x10: TelegramIdInvalid,
    0x14: BlockNumberInvalid,
    0x16: CommandTypeInvalid,
    0x34: TelegrammFormatError,
    0x36: CommandTelegramError,
    0xff: UnknownTelegramError,
    }


class Telegramm(object):
    telegram_types = {"send": 0x41, "fetch": 0x45}
    answer_length = 0

    def __init__(self, telegram_type="send", destination_address=None, device_address=0x7, coordination_flag=0xff):
        if telegram_type not in self.telegram_types:
            raise RuntimeError("TelegrammType invalid. Must be one of %s" % self.telegram_types)
        self._telegram_type = self.telegram_types[telegram_type]

        if not destination_address:
            raise RuntimeError("Destination Address invalid %s" % destination_address)
        self._destination_address = destination_address

        if device_address not in [0x7, 0x8]:
            raise RuntimeError("Device Address is invalid. Valid: %s" % [0x7, 0x8])
        self._device_address = device_address

        self._coordination_flag = coordination_flag

        self._data = bytearray()

    @property
    def data(self):
        return self._data

    def set_data(self, data):
        self._data = data

    def assemble(self):
        # 16 bit (big endian?)
        telegramm_id = 0x0

        # 8 bit
        # self._telegram_type

        # 8 bit - block access = 0x44
        access_type = 0x44

        # 16 bit - (big endian)
        #self._destination_address

        # 16 bit - size of (repeating head data + CRC (big_endian)) in 16bit words !! not byte!
        size = int(round(len(self._data) / 2.0))

        head = pack('>HBB', telegramm_id, self._telegram_type, access_type)
        repeating = pack('<H>HBB', self._destination_address, size, self._coordination_flag, self._device_address)

        crc_data = repeating + self._data
        crc = crc16.crc16xmodem(crc_data, 0xffff)
        crc = pack('<H', crc)

        message = head + repeating + crc_data + crc

        return message

class ContinousDatagram(Telegramm):
    def __init__(self, data):
        """ create a ContinousDatagram from a Buffer """
        # 4byte nulls, 2byte nulls, size (2byte bigendian), coord (1b), addr(1b)
        header = unpack('>iHHBB', data[0:10])

        # must be 0
        if header[0] != 0 or header[1] != 0:
            raise TelegrammError("Invalid leading zeros")

        self._destination_address = header[4]
        self._coordination_flag = header[3]
        self._size = header[2]
        # size must be 772 or 392
        if self._size != 772 and self._size != 392:
            raise TelegrammError("Invalid size (16bit words) for ContinousData valid are %s and not %d - buf %s" % ([392, 772], self._size,
                data))
        # size is in 16bit words - we would like use bytes instead (size * 2)
        # leading 4 '0x00' are not included in size (size + 4)
        self._size = (2 * self._size) + 4
        if len(data) < self._size:
            raise TelegrammError("data too short len(data) = %d" % len(data))

        # little endian
        # (proto minor, proto major, status(2b), timestamp(4b), telegram number(2b), id messdata (2b) = bb, id
        # messdata(2b) = 11)
        header = unpack('<BBHIHHH', data[10:24])
        self._proto_minor = header[0]
        self._proto_major = header[1]
        self._status = header[2]
        self._timestamp = header[3]
        self._telegramm_number = header[4]

        # size begins at offset 2 but crc is calculated without crc field (2 byte)
        self._crc = unpack('<H', data[self._size-2:self._size])[0]
        crc_calc = crc16.crc16xmodem(data[4:self._size-2], 0xffff)
        if crc_calc != self._crc:
            raise TelegrammError("Invalid Crc(data) %s != (calc) %s|size %s" % (self._crc, crc_calc, self._size))

        self._messdata = data[24:self._size-2]
        self._data = data

    @property
    def messdata(self):
        return self._messdata

class Laser(object):
    SLICE_LEN = 3096
    def __init__(self, device='/dev/ttyUSB0', baud_rate=250*1000):
        self._device = device
        self._serial = None
        self._baud_rate = baud_rate
        self._last_pos = -1

    def connect(self):
        if not self._serial:
            self._serial = Serial(self._device, self._baud_rate, timeout=1)

        if not self._serial.isOpen():
            self._serial.open()

    def disconnect(self):
        if self._serial and self._serial.isOpen():
            self._serial.close()

    def send_telegram(self, telegramm):
        message = None
        self._serial.write(telegramm.assemble())
        if telegramm.answer_length != 0:
            message = self._serial.read(telegramm.answer_length)
        else:
            message = self._serial.read(MAX_TELEGRAMM_LENGTH)

        return message

    def read_cont(self):
        buf = None
        if self._last_pos == -1:
            buf = self._serial.read(self.SLICE_LEN)

        pos = buf.find('\x00\x00\x00\x00\x00\x00\x01\x88\xff\x07')
        if pos == -1:
            return None

        if len(buf) - pos > 0:
            # we got a complete datagram
            pass
        else:
            # read more data into buf
            buf += self._serial.read(len(buf) - pos)

        dgram = ContinousDatagram(buf[pos:])
        return dgram
