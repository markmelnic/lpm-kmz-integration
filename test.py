import os, secrets
from kmz_processor import KMZ
from lpm import LPM

obj = LPM(KMZ(), os.getenv('GEOCODE_KEY'), os.getenv('WEATHER_KEY'))
print(obj.get_pollution("Amsterdam"))
