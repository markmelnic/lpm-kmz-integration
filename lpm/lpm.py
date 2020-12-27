import googlemaps, requests, scalg, json
from geopy.distance import geodesic
from datetime import datetime

from .utils import find_pollution_coords

class LPM:
    def __init__(self, kmz_obj, geo_key: str, weather_key: str) -> None:
        self.kmz_obj = kmz_obj
        self.weather_key = weather_key
        self.gmaps = googlemaps.Client(key=geo_key)

    def get_pollution(self, location: str) -> list:
        if type(location) == str:
            user_coords = self._user_location(location)
        else:
            user_coords = location
        item = self.kmz_obj.coords_item(user_coords)
        edges, image = self.kmz_obj.load_images(item[1], single=True, neighbours=True)
        closest_unique_spots = find_pollution_coords(user_coords, edges, image)
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
            if hour > sunset + 1 or hour < sunrise - 1:
                time = item["dt_txt"]
                clouds = item["clouds"]["all"]
                temperature = item["main"]["temp"]
                pressure = item["main"]["pressure"]
                humidity = item["main"]["humidity"]
                datae.append([time, clouds, temperature, pressure, humidity])
        return sorted(datae, key = lambda x: x[1])[0]
