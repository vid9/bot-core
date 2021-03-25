import json
import datetime as dt

import requests
import data.actions.helpers.logic_helper as lh
from bs4 import BeautifulSoup

import os


def get_current_weather(location):
    try:
        url = "https://api.openweathermap.org/data/2.5/weather"
        querystring = {"q": location, "lang": "sl", "units": "metric", "apikey": "ee08894d24be7260bd0abc212093f816"}

        response = requests.request("GET", url, params=querystring)
        weather_obj = response.json(encoding='utf-8')
        return_obj = {
            "type": "current",
            "icon": weather_obj["weather"][0]["icon"],
            "description": weather_obj["weather"][0]["description"],
            "temperature": round(weather_obj["main"]["temp"]),
            "temperature_feel": round(weather_obj["main"]["feels_like"]),
            "humidity": weather_obj["main"]["humidity"],
            "pressure": weather_obj["main"]["pressure"],
            "wind_direction": lh.get_wind_direction(weather_obj["wind"]["deg"]),
            "wind_speed": round(weather_obj["wind"]["speed"] * 3.6),  # km/h
            "visibility": weather_obj["visibility"],
            "name": weather_obj["name"]}
        return return_obj
    except KeyError:
        print(KeyError)
        return {"type": "error",
                "description": "Za kraj {} nisem našel primernih vremenskih podatkov. Želiš informacije za kateri drug kraj?".format(
                    location
                )}


def get_forecast_weather(location, date_number):
    this_folder = os.path.dirname(os.path.abspath(__file__))
    file = os.path.join(this_folder, 'weather_locations.json')
    f = open(file, "r", encoding="utf-8")
    obj = json.loads(f.read())
    lat = 0
    lon = 0
    location_name = ""
    for i in obj:
        if location.lower() == i["name"].lower():
            location_name = i["name"]
            lat = i["coord"]["lat"]
            lon = i["coord"]["lon"]
            break
    if lat == 0:
        # could not find town in the database, return back
        print("could not find town in the database, return back", lat, lon)
        return {"type": "error",
                "description": "Za kraj {} nisem našel primerne vremenske napovedi. Želiš napoved za kateri drug kraj?".format(
                    location
                )}
    try:
        url = "https://api.openweathermap.org/data/2.5/onecall"
        querystring = {"lat": lat,
                       "lon": lon,
                       "exclude": "current,minutely,hourly,alerts",
                       "units": "metric",
                       "lang": "sl",
                       "appid": "ee08894d24be7260bd0abc212093f816"}

        response = requests.request("GET", url, params=querystring)
        weather_obj = response.json()
        return_obj = {
            "type": "forecast",
            "sunrise": weather_obj["daily"][date_number]["sunrise"],
            "sunset": weather_obj["daily"][date_number]["sunset"],
            "daily_morn": round(weather_obj["daily"][date_number]["temp"]["morn"]),
            "daily_day": round(weather_obj["daily"][date_number]["temp"]["day"]),
            "daily_eve": round(weather_obj["daily"][date_number]["temp"]["eve"]),
            "daily_night": round(weather_obj["daily"][date_number]["temp"]["night"]),
            "daily_max": round(weather_obj["daily"][date_number]["temp"]["max"]),
            "daily_min": round(weather_obj["daily"][date_number]["temp"]["min"]),
            "feels_morn": round(weather_obj["daily"][date_number]["feels_like"]["morn"]),
            "feels_day": round(weather_obj["daily"][date_number]["feels_like"]["day"]),
            "feels_eve": round(weather_obj["daily"][date_number]["feels_like"]["eve"]),
            "feels_night": round(weather_obj["daily"][date_number]["feels_like"]["night"]),
            "pressure": weather_obj["daily"][date_number]["pressure"],
            "humidity": weather_obj["daily"][date_number]["humidity"],
            "uvi": weather_obj["daily"][date_number]["uvi"],
            "pop": weather_obj["daily"][date_number]["pop"],
            "wind_direction": lh.get_wind_direction(weather_obj["daily"][date_number]["wind_deg"]),
            "wind_speed": round(weather_obj["daily"][date_number]["wind_speed"] * 3.6),  # km/h
            "description": weather_obj["daily"][date_number]["weather"][0]["description"],
            "icon": weather_obj["daily"][date_number]["weather"][0]["icon"],
            "name": location_name,
        }
        return return_obj
    except KeyError:
        return {"type": "error",
                "description": "Za kraj {} nisem našel primerne vremenske napovedi. Želiš napoved za kateri drug kraj?".format(
                    location
                )}


def get_forecast_slovenia(date_number):
    url = "http://meteo.arso.gov.si/uploads/probase/www/fproduct/text/sl/fcast_si_text.html"

    page = requests.get(url)
    page.encoding = "utf-8"

    soup = BeautifulSoup(page.text, 'html.parser')
    today = dt.datetime.today().weekday()

    if date_number == today:
        return {"type": "forecast", "description": soup.find_all('p')[1].text}
    elif date_number == lh.get_day_number("jutri"):
        return {"type": "forecast", "description": soup.find_all('p')[2].text}
    else:
        return {"type": "forecast", "description": soup.find_all('p')[3].text}


def format_weather_current(weather):
    image = f"http://openweathermap.org/img/wn/{weather['icon']}@4x.png"
    list_element = {'title': f"{weather['temperature']} °C {weather['description']}",
                    'subtitle': f"Občutek zunaj {weather['temperature_feel']} °C \n"
                                f"Vlažnost {weather['humidity']}% \n"
                                f"Pritisk {weather['pressure']} hPa \n"
                                f"Veter {weather['wind_speed']} km/h {weather['wind_direction']}",
                    'image_url': image
                    }
    return [list_element]


def format_weather_forecast(weather):
    image = f"http://openweathermap.org/img/wn/{weather['icon']}@4x.png"
    list_element = {'title': f"{weather['description'].capitalize()}. "
                             f"MAX TEMP {weather['daily_max']} °C, MIN {weather['daily_min']} °C.",
                    'subtitle': f"🌅 {dt.datetime.fromtimestamp(weather['sunrise']).strftime('%#H:%M')}  "
                                f"🌇 {dt.datetime.fromtimestamp(weather['sunset']).strftime('%#H:%M')}  "
                                f"🌧 {round(weather['pop']*100)}%\n"
                                f"Vlažnost {weather['humidity']}%   "
                                f"Pritisk {weather['pressure']} hPa\n"
                                f"Veter {weather['wind_speed']} km/h {weather['wind_direction']}",
                    'image_url': image
                    }
    return [list_element]
