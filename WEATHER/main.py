import requests
from geopy.geocoders import Nominatim



url="https://api.open-meteo.com/v1/forecast"

geolocator = Nominatim(user_agent="city_locator")

city =input("Enter City Name: ")


location = geolocator.geocode(city)
params = {
    "latitude": location.latitude,
    "longitude": location.longitude,
    "current_weather": True
}

response = requests.get(url,params=params)

data=response.json()
ans=data['current_weather']
print(f"CITY IS :{city.upper()}")
print(f"TEMPARATURE IS : {ans['temperature']}")
print(f"WINDSSPEED IS : {ans['windspeed']}")
