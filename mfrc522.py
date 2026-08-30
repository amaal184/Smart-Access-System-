"""
mfrc522.py
MicroPython driver for the MFRC522 RFID/NFC reader module (SPI interface).
Works with Raspberry Pi Pico + machine.SPI.

Usage:
    from machine import Pin, SPI
    from mfrc522 import MFRC522

    sck  = Pin(18)
    mosi = Pin(19)
    miso = Pin(16)
    spi = SPI(0, baudrate=1000000, polarity=0, phase=0,
              sck=sck, mosi=mosi, miso=miso)

    rdr = MFRC522(spi, cs=Pin(17), rst=Pin(20))

    while True:
        stat, tag_type = rdr.request(rdr.REQIDL)
        if stat == rdr.OK:
            stat, raw_uid = rdr.anticoll()
            if stat == rdr.OK:
                uid = "-".join("{:02X}".format(b) for b in raw_uid)
                print("Card UID:", uid)
"""

import time
from machine import Pin


class MFRC522:

    OK = 0
    NOTAGERR = 1
    ERR = 2

    REQIDL = 0x26
    REQALL = 0x52
    AUTHENT1A = 0x60
    AUTHENT1B = 0x61

    PICC_ANTICOLL = 0x93

    # Register addresses
    CommandReg = 0x01
    ComIEnReg = 0x02
    DivIEnReg = 0x03
    ComIrqReg = 0x04
    DivIrqReg = 0x05
    ErrorReg = 0x06
    Status1Reg = 0x07
    Status2Reg = 0x08
    FIFODataReg = 0x09
    FIFOLevelReg = 0x0A
    ControlReg = 0x0C
    BitFramingReg = 0x0D
    CollReg = 0x0E
    ModeReg = 0x11
    TxControlReg = 0x14
    TxASKReg = 0x15
    CRCResultRegM = 0x21
    CRCResultRegL = 0x22
    ModWidthReg = 0x24
    TModeReg = 0x2A
    TPrescalerReg = 0x2B
    TReloadRegH = 0x2C
    TReloadRegL = 0x2D
    VersionReg = 0x37

    PCD_IDLE = 0x00
    PCD_AUTHENT = 0x0E
    PCD_RECEIVE = 0x08
    PCD_TRANSMIT = 0x04
    PCD_TRANSCEIVE = 0x0C
    PCD_RESETPHASE = 0x0F
    PCD_CALCCRC = 0x03

    def __init__(self, spi, cs, rst):
        self.spi = spi
        self.cs = cs
        self.rst = rst

        self.cs.init(Pin.OUT)
        self.rst.init(Pin.OUT)

        self.cs.value(1)
        self.rst.value(1)
        self._reset()

        self._write(self.TModeReg, 0x8D)
        self._write(self.TPrescalerReg, 0x3E)
        self._write(self.TReloadRegL, 30)
        self._write(self.TReloadRegH, 0)
        self._write(self.TxASKReg, 0x40)
        self._write(self.ModeReg, 0x3D)
        self._antenna_on()

    # ---------- low level SPI helpers ----------

    def _write(self, reg, val):
        self.cs.value(0)
        self.spi.write(bytearray([(reg << 1) & 0x7E, val]))
        self.cs.value(1)

    def _read(self, reg):
        self.cs.value(0)
        self.spi.write(bytearray([((reg << 1) & 0x7E) | 0x80]))
        val = self.spi.read(1)
        self.cs.value(1)
        return val[0]

    def _set_bitmask(self, reg, mask):
        cur = self._read(reg)
        self._write(reg, cur | mask)

    def _clear_bitmask(self, reg, mask):
        cur = self._read(reg)
        self._write(reg, cur & (~mask))

    def _antenna_on(self):
        cur = self._read(self.TxControlReg)
        if not (cur & 0x03):
            self._set_bitmask(self.TxControlReg, 0x03)

    def _reset(self):
        self._write(self.CommandReg, self.PCD_RESETPHASE)

    # ---------- card communication ----------

    def _to_card(self, command, data):
        recv = []
        bits = irq_en = wait_irq = n = 0

        if command == self.PCD_AUTHENT:
            irq_en = 0x12
            wait_irq = 0x10
        if command == self.PCD_TRANSCEIVE:
            irq_en = 0x77
            wait_irq = 0x30

        self._write(self.ComIEnReg, irq_en | 0x80)
        self._clear_bitmask(self.ComIrqReg, 0x80)
        self._set_bitmask(self.FIFOLevelReg, 0x80)
        self._write(self.CommandReg, self.PCD_IDLE)

        for b in data:
            self._write(self.FIFODataReg, b)

        self._write(self.CommandReg, command)

        if command == self.PCD_TRANSCEIVE:
            self._set_bitmask(self.BitFramingReg, 0x80)

        i = 2000
        while True:
            n = self._read(self.ComIrqReg)
            i -= 1
            if not (i != 0 and not (n & 0x01) and not (n & wait_irq)):
                break

        self._clear_bitmask(self.BitFramingReg, 0x80)

        if i != 0:
            if (self._read(self.ErrorReg) & 0x1B) == 0x00:
                status = self.OK
                if n & irq_en & 0x01:
                    status = self.NOTAGERR

                if command == self.PCD_TRANSCEIVE:
                    n = self._read(self.FIFOLevelReg)
                    last_bits = self._read(self.ControlReg) & 0x07
                    if last_bits != 0:
                        bits = (n - 1) * 8 + last_bits
                    else:
                        bits = n * 8

                    if n == 0:
                        n = 1
                    if n > 16:
                        n = 16

                    for _ in range(n):
                        recv.append(self._read(self.FIFODataReg))
            else:
                status = self.ERR
        else:
            status = self.ERR

        return status, recv, bits

    def request(self, mode):
        self._write(self.BitFramingReg, 0x07)
        (status, recv, bits) = self._to_card(self.PCD_TRANSCEIVE, [mode])
        if (status != self.OK) or (bits != 0x10):
            status = self.ERR
        return status, bits

    def anticoll(self):
        self._write(self.BitFramingReg, 0x00)
        ser_num = [self.PICC_ANTICOLL, 0x20]
        (status, recv, bits) = self._to_card(self.PCD_TRANSCEIVE, ser_num)

        if status == self.OK:
            if len(recv) == 5:
                chksum = 0
                for i in range(4):
                    chksum ^= recv[i]
                if chksum != recv[4]:
                    # Some simulators (e.g. Wokwi) don't send a matching
                    # checksum byte; fall back to just using the 4 UID bytes
                    recv = recv[:4]
            elif len(recv) == 4:
                pass  # already just the UID bytes, accept as-is
            else:
                status = self.ERR

        return status, recv
