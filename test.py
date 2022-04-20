from dotenv import load_dotenv
load_dotenv()

from os import getenv
from importlib import import_module
lpm = import_module("light-pollution-mapper")
kmz = import_module("kmz-processor")

obj = lpm.LPM(
    kmz.KMZ(),
    getenv('GEOCODE_KEY'),
    getenv('WEATHER_KEY')
)

print(obj.get_pollution("Amsterdam"))
