#!/usr/bin/env python3
import serial
#import time
ser = serial.Serial('/dev/ttyAMA0', 9600, timeout=0, bytesize=serial.EIGHTBITS)
print("connected to: " + ser.portstr)

#print('send...')
#ser.write('2H'.encode('utf-8'))
#print('start...')

while True:
    for line in ser.read():
        line = chr(line)
        if line != '':
            print(line, end='')
            #time.sleep(1)
