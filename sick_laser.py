#!/usr/bin/env python2

import logging
import serial
import crc16
from struct import pack

LOG = logging.getLogger('laser')

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

class Laser(object):
    pass

class RK512(object):
    """ RK512 telegramm used by a Sick Laser S300/S3000 """
    version = 0.1

class Telegramm(object):
    telegram_types = {"send": 0x41, "fetch": 0x45}

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

        message = head + repeating + crc_data + crc

        return message
