from datetime import datetime
from enum import Enum
import serial

# fix rpi uart before: https://www.raspberrypi.org/documentation/configuration/uart.md
ser = serial.Serial('/dev/ttyAMA0', 9600, timeout=0, bytesize=serial.EIGHTBITS) # todo: rate, fix rpi uart

class S(Enum):
    OFF = 0
    STRIPE = 1
    MIDDLE = 2
MIN = S.OFF
MAX = S.MIDDLE

def now():
    return datetime.now()

def get_sunset():
    return get_time(SUNSET_TIMES[now().month - 1])

# sunset times for 12 months
# generator here: ./get-sun-times.py
SUNSET_TIMES = ['16:07', '17:02', '18:05', '19:08', '20:09', '21:03', '21:16', '20:34', '19:22', '18:03', '16:48', '16:01']

state = S.STRIPE if now() >= get_sunset() else S.OFF
latest_manual_action_time = None

def get_time(string):
    [hour, minute] = string.split(':')
    return now().replace(hour = hour, minute = minute)

def onSig(direction):
    global latest_manual_action_time

    dimm(+1 if direction == 'R' else -1)
    latest_manual_action_time = now()
    for i in [1, 2]: # lamp levels
        ser.write(f"{i}{'H' if level >= {i} else 'L'}")

def changed_manually_recently():
    return (now() - latest_manual_action_time).seconds > 30 * 60 # todo

# brighter / darken
def dimm(delta):
    global state
    level = state.value + delta
    if level > MAX.value or level < MIN.value:
        ser.write("vE") # error feedback
    else:
        state = S(level)


#
# main
#

while True:
    global state
    command = ser.readString() # todo

    if command == "turn R":
        onSig("R")
    elif command == "turn L":
        onSig("L")
    if state == S.OFF:
        None
    elif state == S.STRIPE:
        None
    elif state == S.MIDDLE:
        None

    if not changed_manually_recently():
        if state == S.OFF and now() > get_time('08:40'):
            dimm(+1)

        if now() >= get_sunset():
            dimm(+1)

