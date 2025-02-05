import requests
from datetime import datetime, timedelta, timezone
from config import OPENWEATHER_API_KEY


def get_temperature(city):
    if not city:
        return None
    url = 'http://api.openweathermap.org/data/2.5/weather'
    params = {
        'q': city,
        'appid': OPENWEATHER_API_KEY,
        'units': 'metric',
        'lang': 'ru'
    }
    try:
        response = requests.get(url, params=params)
        data = response.json()
        if data.get('cod') != 200:
            return None
        return data['main']['temp']
    except:
        return None


def get_local_time_for_city(city):
    if not city:
        return datetime.now(timezone.utc)
    url = 'http://api.openweathermap.org/data/2.5/weather'
    params = {
        'q': city,
        'appid': OPENWEATHER_API_KEY
    }
    try:
        resp = requests.get(url, params=params)
        data = resp.json()
        if data.get('cod') != 200:
            return datetime.now(timezone.utc)
        offset_seconds = data.get('timezone', 0)
        utc_now = datetime.now(timezone.utc)
        local_now = utc_now + timedelta(seconds=offset_seconds)
        return local_now
    except:
        return datetime.now(timezone.utc)
