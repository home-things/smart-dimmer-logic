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

def get_time(string):
    [hour, minute] = string.split(':')
    return now().replace(hour = int(hour), minute = int(minute))

def now():
    return datetime.now()

def get_sunset():
    return get_time(SUNSET_TIMES[now().month - 1])

# brighter / darken
def update_state(delta):
    global state
    level = state.value + delta
    if level > MAX.value or level < MIN.value:
        ser.write("vE") # error feedback
    else:
        state = S(level)

def dimm(state):
    global latest_manual_action_time
    latest_manual_action_time = now()
    for i in [1, 2]: # lamp levels
        ser.write('' + str(i) + ('H' if state.value >= i else 'L'))

def changed_manually_recently():
    return (now() - latest_manual_action_time).seconds > 30 * 60 # todo


# sunset times for 12 months
# generator here: ./get-sun-times.py
SUNSET_TIMES = ['16:07', '17:02', '18:05', '19:08', '20:09', '21:03', '21:16', '20:34', '19:22', '18:03', '16:48', '16:01']

state = S.STRIPE if now() >= get_sunset() else S.OFF
dimm(state)
latest_manual_action_time = datetime.min

#
# main
#

while True:
    command = ser.read_until('\0') # todo

    if command == "turn R":
        update_state(+1)
        dimm(state)
    elif command == "turn L":
        update_state(-1)
        dimm(state)
    if state == S.OFF:
        pass
    elif state == S.STRIPE:
        pass
    elif state == S.MIDDLE:
        pass

    if not changed_manually_recently():
        if state == S.OFF and now() > get_time('08:40'):
            update_state(+1)
            dimm(state)

        if now() >= get_sunset():
            update_state(+1)
            dimm(state)

