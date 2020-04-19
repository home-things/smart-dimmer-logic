from datetime import datetime
from enum import Enum
import serial

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

def get_sunset():
    return get_time(SUNSET_TIMES[now().month - 1])

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
    global latest_manual_action_time
    latest_manual_action_time = now()
    for i in [1, 2]: # lamp levels
        send(str(i) + ('H' if state.value >= i else 'L'))

def changed_manually_recently():
    return (now() - latest_manual_action_time).seconds <= 30 * 60 # todo


# sunset times for 12 months
# generator is here: ./get-sun-times.py
SUNSET_TIMES = ['16:07', '17:02', '18:05', '19:08', '20:09', '21:03', '21:16', '20:34', '19:22', '18:03', '16:48', '16:01']

state = S.STRIPE if now() >= get_sunset() else S.OFF
dimm(state)
latest_manual_action_time = datetime.min

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
        print(f"has changed recently?: {changed_manually_recently()}")
        print(f"state: {state}")

    elif not changed_manually_recently():
        if state == S.OFF and now() > get_time('08:40'):
            inc_state(+1)
            dimm(state)
            print("dimmed up automatically: good morning")

        elif now() >= get_sunset():
            inc_state(+1)
            dimm(state)
            print("dimmed up automatically: good evening")

        elif now() >= get_sunset() + 3:
            if state.value > S.STRIPE.value:
                set_state(S.STRIPE)
                dimm(state)
                print("dimmed down automatically: good evening")

        elif now() >= get_sunset() + 5:
            if state.value > S.STRIPE.value:
                set_state(S.OFF)
                dimm(state)
                print("dimmed down automatically: good night")

        print(f"state: {state}")

