#!/usr/bin/env python3
import serial
import time
ser = serial.Serial('/dev/ttyAMA0', 9600, timeout=0, bytesize=serial.EIGHTBITS)

print('send...')
ser.write(2)
print('start...')
while True:
  for line in ser.readline():
    if chr(line) != '':
      print(chr(line), end='')
      #time.sleep(1)
      # ser.write(1)
