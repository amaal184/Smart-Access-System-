"""
main.py
Smart Access System - Raspberry Pi Pico + Wokwi
Integrates: RFID-RC522, I2C LCD, Servo (door lock), LEDs, Buzzer
"""

from machine import Pin, SPI, I2C, PWM
import time

from mfrc522 import MFRC522
from pico_i2c_lcd import I2cLcd


# =========================================================
# 1) PIN SETUP  (matches the wiring table we agreed on)
# =========================================================

# --- RFID (SPI) ---
spi = SPI(0, baudrate=1000000, polarity=0, phase=0,
          sck=Pin(18), mosi=Pin(19), miso=Pin(16))
rdr = MFRC522(spi, cs=Pin(17), rst=Pin(20))

# --- LCD (I2C) ---
i2c = I2C(0, sda=Pin(4), scl=Pin(5), freq=400000)
lcd = I2cLcd(i2c, 0x27, 2, 16)      # try 0x3F if 0x27 doesn't work

# --- Servo (door) ---
servo = PWM(Pin(15))
servo.freq(50)

# --- LEDs ---
led_green = Pin(14, Pin.OUT)
led_red = Pin(13, Pin.OUT)

# --- Buzzer (PWM so it makes an actual audible tone in Wokwi) ---
buzzer = PWM(Pin(12))
buzzer.duty_u16(0)


# =========================================================
# 2) REGISTERED USERS  (fill in real UIDs after testing)
# =========================================================

users = {
    "55:77:CC:00": {"name": "Ahmed", "role": "Employee"},   # Yellow Card
    "01:03:04:00": {"name": "Sara",  "role": "Manager"},    # Blue Card
    "11:33:44:00": {"name": "Omar",  "role": "Employee"},   # Green Card
    "AA:CC:00:00": {"name": "Menna", "role": "Admin"},      # Red Card
}


# =========================================================
# 3) STATE VARIABLES
# =========================================================

failed_attempts = 0
MAX_FAILED_ATTEMPTS = 4
DOOR_OPEN_SECONDS = 5


# =========================================================
# 4) HELPER FUNCTIONS  (each one does ONE job)
# =========================================================

def uid_to_string(raw_uid):
    """Convert the list of UID bytes into a readable string."""
    return ":".join("{:02X}".format(b) for b in raw_uid)


def beep(frequency=1000, duration=0.3):
    """Play an audible tone on the passive buzzer using PWM."""
    buzzer.freq(frequency)
    buzzer.duty_u16(32767)   # 50% duty cycle -> audible tone
    time.sleep(duration)
    buzzer.duty_u16(0)       # silence


def show_idle():
    lcd.clear()
    lcd.putstr("Please scan\nyour card")


def open_door():
    servo.duty_u16(7864)      # ~90 degrees (open)


def close_door():
    servo.duty_u16(1638)      # ~0 degrees (closed)


def grant_access(user):
    global failed_attempts
    failed_attempts = 0

    lcd.clear()
    lcd.putstr("Welcome " + user["name"] + "\nRole: " + user["role"])

    led_green.value(1)
    open_door()
    time.sleep(DOOR_OPEN_SECONDS)
    close_door()
    led_green.value(0)

    show_idle()


def deny_access():
    global failed_attempts
    failed_attempts += 1

    lcd.clear()
    lcd.putstr("Access Denied\nUnknown Card")

    led_red.value(1)
    time.sleep(0.5)
    led_red.value(0)

    if failed_attempts >= MAX_FAILED_ATTEMPTS:
        trigger_alarm()
    else:
        show_idle()


def trigger_alarm():
    global failed_attempts

    lcd.clear()
    lcd.putstr("ALERT!\nToo many tries")

    for _ in range(6):
        led_red.value(1)
        beep(1500, 0.2)
        led_red.value(0)
        time.sleep(0.2)

    failed_attempts = 0
    show_idle()


# =========================================================
# 5) MAIN LOOP
# =========================================================

close_door()
show_idle()

while True:
    status, tag_type = rdr.request(rdr.REQIDL)

    if status == rdr.OK:
        status, raw_uid = rdr.anticoll()
        if status == rdr.OK:
            card_uid = uid_to_string(raw_uid)
            print("Card detected, UID:", card_uid)

            if card_uid in users:
                grant_access(users[card_uid])
            else:
                deny_access()

            time.sleep(1)   # small pause to avoid double-reading the same card
