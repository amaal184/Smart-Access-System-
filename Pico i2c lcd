"""
pico_i2c_lcd.py
Implements the I2C-backpack (PCF8574) hardware layer for a HD44780
LCD, built on top of lcd_api.py, for use with machine.I2C on the
Raspberry Pi Pico.

Usage:
    from machine import I2C, Pin
    from pico_i2c_lcd import I2cLcd

    i2c = I2C(0, sda=Pin(4), scl=Pin(5), freq=400000)
    lcd = I2cLcd(i2c, 0x27, 2, 16)   # address, rows, columns

    lcd.putstr("Hello world")
"""

import time
from machine import I2C
from lcd_api import LcdApi


class I2cLcd(LcdApi):

    # PCF8574 pin mapping to the HD44780 lines
    MASK_RS = 0x01
    MASK_RW = 0x02
    MASK_E = 0x04
    SHIFT_BACKLIGHT = 3
    SHIFT_DATA = 4

    def __init__(self, i2c, i2c_addr, num_lines, num_columns):
        self.i2c = i2c
        self.i2c_addr = i2c_addr
        self.i2c.writeto(self.i2c_addr, bytearray([0]))
        time.sleep_ms(20)

        # Initialize in 4-bit mode
        self.hal_write_init_nibble(self.LCD_FUNCTION_RESET)
        time.sleep_ms(5)
        self.hal_write_init_nibble(self.LCD_FUNCTION_RESET)
        time.sleep_ms(1)
        self.hal_write_init_nibble(self.LCD_FUNCTION_RESET)
        time.sleep_ms(1)
        self.hal_write_init_nibble(self.LCD_FUNCTION)
        time.sleep_ms(1)

        LcdApi.__init__(self, num_lines, num_columns)

        cmd = self.LCD_FUNCTION
        if num_lines > 1:
            cmd |= self.LCD_FUNCTION_2LINES
        self.hal_write_command(cmd)

    def hal_write_init_nibble(self, nibble):
        byte = ((nibble >> 4) & 0x0F) << self.SHIFT_DATA
        self.i2c.writeto(self.i2c_addr, bytearray([byte | self.MASK_E]))
        self.i2c.writeto(self.i2c_addr, bytearray([byte]))

    def hal_backlight_on(self):
        self.i2c.writeto(self.i2c_addr,
                          bytearray([1 << self.SHIFT_BACKLIGHT]))

    def hal_backlight_off(self):
        self.i2c.writeto(self.i2c_addr, bytearray([0]))

    def hal_write_command(self, cmd):
        byte = ((self.backlight << self.SHIFT_BACKLIGHT) |
                (((cmd >> 4) & 0x0F) << self.SHIFT_DATA))
        self.i2c.writeto(self.i2c_addr, bytearray([byte | self.MASK_E]))
        self.i2c.writeto(self.i2c_addr, bytearray([byte]))
        byte = ((self.backlight << self.SHIFT_BACKLIGHT) |
                ((cmd & 0x0F) << self.SHIFT_DATA))
        self.i2c.writeto(self.i2c_addr, bytearray([byte | self.MASK_E]))
        self.i2c.writeto(self.i2c_addr, bytearray([byte]))
        if cmd <= 3:
            time.sleep_ms(5)

    def hal_write_data(self, data):
        byte = (self.MASK_RS |
                (self.backlight << self.SHIFT_BACKLIGHT) |
                (((data >> 4) & 0x0F) << self.SHIFT_DATA))
        self.i2c.writeto(self.i2c_addr, bytearray([byte | self.MASK_E]))
        self.i2c.writeto(self.i2c_addr, bytearray([byte]))
        byte = (self.MASK_RS |
                (self.backlight << self.SHIFT_BACKLIGHT) |
                ((data & 0x0F) << self.SHIFT_DATA))
        self.i2c.writeto(self.i2c_addr, bytearray([byte | self.MASK_E]))
        self.i2c.writeto(self.i2c_addr, bytearray([byte]))
