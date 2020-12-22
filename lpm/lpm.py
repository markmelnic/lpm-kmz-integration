import googlemaps, requests, scalg, json
from math import sqrt
from scipy.spatial import distance
from geopy.distance import geodesic
from datetime import datetime

from lpm.settings import COLORS, LO_P

class LPM:
    def __init__(self, kmz_obj, geo_key: str, weather_key: str) -> None:
        self.kmz_obj = kmz_obj
        self.weather_key = weather_key
        self.gmaps = googlemaps.Client(key=geo_key)

    def get_pollution(self, location: str) -> list:
        user_coords = self._user_location(location)
        item = self.kmz_obj.coords_item(user_coords)
        image = self.kmz_obj.load_images(item[1], single=True)
        closest_unique_spots = self._find_pollution_coords(user_coords, item, image)
        for i, spot in enumerate(closest_unique_spots):
            elevation = self.gmaps.elevation(spot)[0]['elevation']
            weather = self._coords_weather(spot)
            distance = geodesic(user_coords,spot).km
            closest_unique_spots[i] = [spot, distance, elevation] + weather
        scores = scalg.score_columns(closest_unique_spots, [1, 2, 4], [0, 1, 0])
        return user_coords, sorted(scores, key = lambda x: x[-1])[-1]

    def _user_location(self, location: str) -> tuple:
        geocoded_location = self.gmaps.geocode(location)
        lat = geocoded_location[0]["geometry"]["location"]["lat"]
        lng = geocoded_location[0]["geometry"]["location"]["lng"]
        return (lat, lng)

    def _coords_weather(self, coords: tuple) -> list:
        req_url = "https://api.openweathermap.org/data/2.5/forecast?units=metric&lat={}&lon={}&appid={}".format(coords[0], coords[1], self.weather_key)
        response = json.loads(requests.get(req_url).content)
        sunrise = datetime.fromtimestamp(response["city"]['sunrise']).hour
        sunset = datetime.fromtimestamp(response["city"]['sunset']).hour
        datae = []
        for item in response["list"]:
            hour = datetime.fromtimestamp(item["dt"]).hour
            if hour > sunset or hour < sunrise:
                time = item["dt_txt"]
                clouds = item["clouds"]["all"]
                temperature = item["main"]["temp"]
                pressure = item["main"]["pressure"]
                humidity = item["main"]["humidity"]
                datae.append([time, clouds, temperature, pressure, humidity])
        return sorted(datae, key = lambda x: x[1])[0]

    def _find_pollution_coords(self, user_coords: list, item: list, image: bytes) -> list:
        def _matrix_geo_coords(matrix_coords: list) -> tuple:
            lat = item[3] - ((item[3] - item[4]) / width * matrix_coords[1])
            lng = item[6] + ((item[5] - item[6]) / height * matrix_coords[0])
            return (lat, lng)

        def _closest_color(rgb: list) -> tuple:
            r, g, b = rgb
            color_diffs = []
            for color in COLORS:
                cr, cg, cb = color
                color_diff = sqrt(abs(r - cr) ** 2 + abs(g - cg) ** 2 + abs(b - cb) ** 2)
                color_diffs.append((color_diff, color))
            return min(color_diffs)[1]

        def _closest(node: tuple, nodes: list) -> tuple:
            closest_px = distance.cdist([node], nodes).argmin()
            return nodes[closest_px]

        width, height = image.size
        wpx = int(height * (user_coords[1] - item[6]) / (item[5] - item[6]))
        hpx = width - int(width * (user_coords[0] - item[4]) / (item[3] - item[4]))
        pixelmap = image.load()
        data = {}
        for c in LO_P:
            data[LO_P.index(c)] = []
        for i in range(int(width / 2)):
            for j in range(int(height / 2)):
                color = _closest_color(pixelmap[i * 2, j * 2])
                for c in LO_P:
                    if color == c:
                        data[LO_P.index(c)].append([i * 2, j * 2])

        closest_unique_spots = [
            _matrix_geo_coords(_closest((wpx, hpx), data[LO_P.index(c)])) for c in LO_P
        ]
        return closest_unique_spots
