import googlemaps, requests, scalg, json
from math import sqrt
from scipy.spatial import distance
from geopy.distance import geodesic
from datetime import datetime

from lpm.settings import COLORS, LO_P

PX_SKIP = 10

class LPM:
    def __init__(self, kmz_obj, geo_key: str, weather_key: str) -> None:
        self.kmz_obj = kmz_obj
        self.weather_key = weather_key
        self.gmaps = googlemaps.Client(key=geo_key)

    def get_pollution(self, location: str) -> list:
        user_coords = self._user_location(location)
        item = self.kmz_obj.coords_item(user_coords)
        edges, image = self.kmz_obj.load_images(item[1], single=True, neighbours=True)
        closest_unique_spots = self._find_pollution_coords(user_coords, edges, image)
        for i, spot in enumerate(closest_unique_spots):
            elevation = self.gmaps.elevation(spot)[0]['elevation']
            weather = self._coords_weather(spot)
            distance = geodesic(user_coords,spot).km
            closest_unique_spots[i] = [spot, distance, elevation] + weather
        scored = scalg.score_columns(closest_unique_spots, [1, 2, 4], [0, 1, 0])
        return user_coords, sorted(scored, key = lambda x: x[-1])[-1]

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

    def _find_pollution_coords(self, user_coords: list, edges: list, image: bytes) -> list:
        def _matrix_geo_coords(matrix_coords: list) -> tuple:
            lat = edges[0] - ((edges[0] - edges[1]) / width * matrix_coords[1])
            lng = edges[3] + ((edges[2] - edges[3]) / height * matrix_coords[0])
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
        wpx = int(height * (user_coords[1] - edges[3]) / (edges[2] - edges[3]))
        hpx = width - int(width * (user_coords[0] - edges[1]) / (edges[0] - edges[1]))

        pixelmap = image.load()

        '''
        data = {}
        for i, c in enumerate(LO_P):
            data[i] = []
        for i in range(int(width / PX_SKIP)):
            for j in range(int(height / PX_SKIP)):
                color = _closest_color(pixelmap[i * PX_SKIP, j * PX_SKIP])
                for c in LO_P:
                    if color == c:
                        data[LO_P.index(c)].append([i * PX_SKIP, j * PX_SKIP])
        
        return [_matrix_geo_coords(_closest((wpx, hpx), data[i])) for i, c in enumerate(LO_P)]
        '''

        ilev = 0
        cus = [] # closest_unique_spots
        indexed_colors = []
        stopper = True
        while not len(cus) == len(LO_P) and stopper:
            ilev += 1
            layer = []
            # top row
            wpos = wpx - ilev
            for i in range(hpx - ilev, hpx + ilev):
                layer.append([wpos, i])
            # right column
            hpos = hpx + ilev
            for i in range(wpx - ilev, wpx + ilev):
                layer.append([i, hpos])
            # bottom row
            wpos = wpx + ilev
            for i in range(hpx - ilev + 1, hpx + ilev + 1):
                layer.append([wpos, i])
            # left column
            hpos = hpx - ilev
            for i in range(wpx - ilev + 1, wpx + ilev + 1):
                layer.append([i, hpos])

            for px in layer:
                try:
                    color = _closest_color(pixelmap[px[0], px[1]])
                except IndexError:
                    stopper = False
                    break
                if not color in indexed_colors and color in LO_P:
                    cus.append(_matrix_geo_coords(px))
                    indexed_colors.append(color)

        return cus
