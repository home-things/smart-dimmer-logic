import serial
ser = serial.Serial('/dev/uart1')
while True:
    command = ser.readString()
    if command == "sig R":
        onSig("R")
    elif command == "sig L":
        onSig("L")
 
    if state == 'off':
        nope
    elif state == 'stripe':
        nope
    elif state == 'middle':
        nope


    # 
