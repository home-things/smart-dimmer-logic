import os
from datetime import datetime, timedelta
from enum import Enum
import serial
from threading import Timer
import paho.mqtt.client as mqtt
from time import sleep

DIR = os.path.dirname(os.path.abspath(__file__))
MQTT_DOMAIN = '192.168.1.68' #'rpi4.local'
MQTT_TOPIC_STATE = "bedroom/light/state" # >> 0 | 1 | 2
MQTT_TOPIC_SW_STATE = "bedroom/light/switch_state" # >> ON | OFF
MQTT_TOPIC_CMD = "bedroom/light/dimm" # << 0 | 1 | 2
MQTT_TOPIC_SW_CMD = "bedroom/light/switch" # << ON | OFF

latest_action_time = datetime.fromtimestamp(0).min # epoch 
is_mqtt_connected = False


class S(Enum):
    UNKNOWN = -1
    OFF = 0
    STRIPE = 1
    MIDDLE = 2
MIN = S.OFF
MAX = S.MIDDLE

class D(Enum):
    UP = +1
    DOWN = -1

rule_triggered = {}


from threading import Timer


def debounce(wait):
    """ Decorator that will postpone a functions
        execution until after wait seconds
        have elapsed since the last time it was invoked. """
    def decorator(fn):
        def debounced(*args, **kwargs):
            def call_it():
                fn(*args, **kwargs)
            try:
                debounced.t.cancel()
            except(AttributeError):
                pass
            debounced.t = Timer(wait, call_it)
            debounced.t.start()
        return debounced
    return decorator

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
    return now().replace(hour = int(hour), minute = int(minute), second=0, microsecond=0)

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
        f.write('ON' if is_on else 'OFf')

# immutable
def inc_state(delta, is_auto):
    level = state.value + delta.value
    if level > MAX.value or level < MIN.value:
        if not is_auto: send('vB') # error feedback
        return state
    else:
        return S(level)

#def set_state(next_state):
#    global state
#    state = new_state

# low level api
#@debounce(0.233)
def _dimm(new_state):
    global state
    global latest_action_time
    if state == new_state: return

    state = new_state
    latest_action_time = now()

    for i in [1, 2]: # lamp levels
        is_on = new_state.value >= i
        send(str(i) + ('H' if is_on else 'L'))
        store(i, is_on)
        print("publishing state over mqtt...")
        mqttc.publish(MQTT_TOPIC_STATE, (state.value), retain=True)
        mqttc.publish(MQTT_TOPIC_SW_STATE, 'ON' if state.value > 0 else 'OFf', retain=True)

# @param {D.UP|D.DOWN} delta
def inc_dimm(delta, is_auto):
    new_state = inc_state(delta, is_auto)
    print(f"inc_dimm. state: {state}, new: {new_state}")
    _dimm(new_state)

# Задаём и направление и ожидаемое значение
# Отклоняется, если чтобы выставить новое значение придётся пойти по иному направлению
# @param {D.UP|D.DOWN} delta
def inc_dimm_to(new_state, delta, is_auto):
    global state
    if new_state == state: return
    if (delta.value > 0) != (new_state.value > state.value): return
    new_state = inc_state(delta, is_auto)
    _dimm(new_state)

def changed_recently():
    global latest_action_time
    return (now() - latest_action_time).seconds <= 15 * 60

def ensure_trigger(name):
    if rule_triggered.get(name) == True: return False

    rule_triggered[name] = True
    return True



#
# INIT
#


# sunset times for 12 months
# generator is here: ./get-sun-times.py
SUNSET_TIMES = ['16:07', '17:02', '18:05', '19:08', '20:09', '21:03', '21:16', '20:34', '19:22', '18:03', '16:48', '16:01']

state = S.UNKNOWN
prev_state = state


#
# === Serial

# First Run Note: fix rpi uart before: https://www.raspberrypi.org/documentation/configuration/uart.md
# timeout -- that's why readline() get full command string at once
ser = serial.Serial('/dev/ttyAMA0', 9600, timeout=1, bytesize=serial.EIGHTBITS)
PRINT_SER = True

print(f"connected to: {ser.portstr}")



#
# === MQTT

print("[mqtt] initing...")
mqttc = mqtt.Client(client_id = "smart-dimmer-bedroom1", clean_session = False)

def on_message(mqttc, userdata, message):
    print("%s %s" % (message.topic, message.payload))
    if message.topic == MQTT_TOPIC_CMD:
      print('[mqtt] >> dimm', message.payload)
    elif message.topic == MQTT_TOPIC_SW_CMD:
      print('[mqtt] >> ON|OFF', message.payload) 

def on_connect(mqttc, userdata, flags, rc):
    global latest_action_time
    global is_mqtt_connected

    print("Connected with result code "+str(rc))
    print(f"[mqtt] subscribing... {MQTT_TOPIC_CMD}")
    mqttc.subscribe(MQTT_TOPIC_CMD)
    mqttc.subscribe(MQTT_TOPIC_SW_CMD)
    print("[mqtt] subscribed")
    
    #
    # State init
    print("initialize controller device status...")
    if (now() < get_sunset() + timedelta(hours = 3) and now() >= get_time('08:40')):
        new_state = S.STRIPE 
    else:
        new_state = S.OFF
    _dimm(new_state)
    latest_action_time = datetime.min

    print(f"Initial state: {state}")
    is_mqtt_connected = True


mqttc.enable_logger(logger=None)
mqttc.on_connect = on_connect
mqttc.on_message = on_message
print("[mqtt] connecting...")
mqttc.connect(MQTT_DOMAIN)

# mqttc.loop_forever()
mqttc.loop_start() # loop thread


#
# main
#

while True:
    #mqttc.loop() # process new mqtt messages
    #sleep(.01)
    if not is_mqtt_connected: continue 

    command = recv()

    if command in ["turn L", "turn R"]:
        print(f"command: '{command}'")
        inc_dimm(D.UP if command == "turn R" else D.DOWN, is_auto = False)
        print(f"has changed recently?: {changed_recently()}")
        print(f"state: {state}")

    # Выключение на ночь делаем даже если недавно был включен свет
    if now_minute() >= get_time('01:30') and now_minute() <= get_time('03:30'): #get_sunset() + timedelta(hours = 5):
        if ensure_trigger('good_night'): 
            inc_dimm_to(S.OFF, D.DOWN, is_auto = True)
            print("dimmed down automatically: good night")

    elif now_minute() >= get_time('00:30') and now_minute() <= get_time('02:30'): #get_sunset() + timedelta(hours = 5):
        if ensure_trigger('good_night'): 
            inc_dimm_to(S.OFF, D.DOWN, is_auto = True)
            print("dimmed down automatically: good night")

    elif now_minute() >= get_time('23:30'): #get_sunset() + timedelta(hours = 5):
        if ensure_trigger('good_night'): 
            inc_dimm_to(S.OFF, D.DOWN, is_auto = True)
            print("dimmed down automatically: good night")

    elif not changed_recently():
        if now_minute() >= get_sunset() + timedelta(hours = 3):
            if ensure_trigger('good_evening'): 
                inc_dimm_to(S.STRIPE, D.UP, is_auto = True)
                print("dimmed down automatically: good evening")

#        elif now_minute() >= get_sunset():
#            if ensure_trigger('good_day'): 
#                inc_dimm(D.UP, is_auto = True)
#                print("dimmed up automatically: good evening")

        elif now_minute() >= get_time('08:40'):
            if ensure_trigger('morning'): 
                inc_dimm_to(S.STRIPE, D.UP, is_auto = True)
                print("dimmed up automatically: good morning")


    if now_minute() == get_time('04:00'):
        rule_triggered.clear()

    if prev_state != state: print(f"new state: {state}")
    prev_state = state

