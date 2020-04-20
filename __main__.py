import os
from datetime import datetime, timedelta
from enum import Enum
import serial

DIR = os.path.dirname(os.path.abspath(__file__))

# fix rpi uart before: https://www.raspberrypi.org/documentation/configuration/uart.md
# timeout -- that's why readline() get full command string at once
ser = serial.Serial('/dev/ttyAMA0', 9600, timeout=1, bytesize=serial.EIGHTBITS)
PRINT_SER = True

print(f"connected to: {ser.portstr}")

class S(Enum):
    OFF = 0
    STRIPE = 1
    MIDDLE = 2
MIN = S.OFF
MAX = S.MIDDLE

def send(string):
    if PRINT_SER: print(f"send <<< {string}")
    ser.write(string.encode('utf-8'))
    ser.flush()

def recv():
    line = ser.readline().decode('utf-8').strip()
    if PRINT_SER and line != '': print(f"recv >>> {line}")
    return line

    #line = ''
    #for byte in ser.read():
    #    char = chr(byte)
    #    if PRINT_SER and char != '': print(char, end='')
    #    line += char
    #return line


def get_time(string):
    [hour, minute] = string.split(':')
    return now().replace(hour = int(hour), minute = int(minute))

def now():
    return datetime.now()

def now_minute():
    return now().replace(second=0, microsecond=0)

def today():
    return now().replace(hour=0, minute=0, second=0, microsecond=0)

def get_sunset():
    return get_time(SUNSET_TIMES[now().month - 1])

def store(lamp_no, is_on):
    with open(f"{DIR}/.state/{lamp_no}", 'w+') as f:
        f.write('on' if is_on else 'off')

# brighter / darken
def inc_state(delta):
    global state
    level = state.value + delta
    if level > MAX.value or level < MIN.value:
        send('vB') # error feedback
    else:
        state = S(level)

def set_state(next_state):
    global state
    state = new_state

# brighter / darken
def dimm(state):
    global latest_action_time
    latest_action_time = now()
    for i in [1, 2]: # lamp levels
        is_on = state.value >= i
        send(str(i) + ('H' if is_on else 'L'))
        store(i, is_on)

def changed_recently():
    return (now() - latest_action_time).seconds <= 30 * 60 # todo


# sunset times for 12 months
# generator is here: ./get-sun-times.py
SUNSET_TIMES = ['16:07', '17:02', '18:05', '19:08', '20:09', '21:03', '21:16', '20:34', '19:22', '18:03', '16:48', '16:01']

if (now() < get_sunset() + timedelta(hours = 3) and now() >= get_time('08:40')):
    state = S.STRIPE 
else:
    state = S.OFF
dimm(state)
latest_action_time = datetime.min

print(f"Initial state: {state}")

#
# main
#

while True:
    command = recv()
    if not command: continue

    if command in ["turn L", "turn R"]:
        print(f"command: '{command}'")
        inc_state(+1 if command == "turn R" else -1)
        dimm(state)
        print(f"has changed recently?: {changed_recently()}")
        print(f"state: {state}")

    elif not changed_recently():
        if state == S.OFF and now_minute() == get_time('08:40'):
            inc_state(+1)
            dimm(state)
            print("dimmed up automatically: good morning")

        elif now_minute() == get_sunset():
            inc_state(+1)
            dimm(state)
            print("dimmed up automatically: good evening")

        elif now_minute() == get_sunset() + timedelta(hours = 3):
            if state.value > S.STRIPE.value:
                set_state(S.STRIPE)
                dimm(state)
                print("dimmed down automatically: good evening")

        elif now_minute() == get_sunset() + timedelta(hours = 5):
            if state.value > S.STRIPE.value:
                set_state(S.OFF)
                dimm(state)
                print("dimmed down automatically: good night")

        print(f"state: {state}")

