#!/usr/bin/env python3
import requests
from pytz import timezone
from datetime import datetime

# moscow geolocation
LAT = 55.755825
LNG = 37.617298

# https://sunrise-sunset.org/api
URL = f"https://api.sunrise-sunset.org/json?lat={LAT}&lng={LNG}&formatted=0"

urls = [
    f"{URL}&date=2020-{month:02d}-01" 
    for month in range(1, 12 + 1)
]

resps = [requests.get(url).json()['results'] for url in urls]
# e.g.
{
        'sunrise': '2020-01-01T05:58:55+00:00',
        'sunset': '2020-01-01T13:07:10+00:00',
        'solar_noon': '2020-01-01T09:33:02+00:00',
        'day_length': 25695,
        'civil_twilight_begin': '2020-01-01T05:12:43+00:00',
        'civil_twilight_end': '2020-01-01T13:53:21+00:00'
} 

sunset_times = [
    datetime.fromisoformat(r['sunset'])
        .astimezone(timezone('Europe/Moscow'))
        .strftime('%H:%M')
    for r in resps
]

print(sunset_times)
# e.g.
['16:07', '17:02', '18:05', '19:08', '20:09', '21:03', '21:16', '20:34', '19:22', '18:03', '16:48', '16:01']

