import datetime as dt


def get_day_number(day):
    current_day = dt.datetime.today().weekday()
    forecast_day = -1
    day = day.lower()
    if day == "danes":
        forecast_day = current_day
    elif day == "jutri":
        forecast_day = current_day + 1
    elif day == "pojutrišnjem":
        forecast_day = current_day + 2
    elif day == "ponedeljek":
        forecast_day = 0
    elif day == "torek":
        forecast_day = 1
    elif day == "sreda":
        forecast_day = 2
    elif day == "četrtek":
        forecast_day = 3
    elif day == "petek":
        forecast_day = 4
    elif day == "sobota":
        forecast_day = 5
    elif day == "nedelja":
        forecast_day = 6

    if forecast_day < 0:
        return None

    forecast_day = (
        forecast_day % 7
    )  # if user searched by today/tomorrow/day after tomorrow, we need to make sure that forecast day is valid

    if forecast_day - current_day >= 0:  # if we want forecast for a day in this week
        return forecast_day - current_day
    else:  # add 1 week and subtract current day
        return (forecast_day + 7) - current_day


def get_day_date(day):
    day_number = get_day_number(day)
    try:
        res_day = dt.datetime.today() + dt.timedelta(days=day_number)
    except TypeError:
        return None
    return res_day.strftime("%m. %d. %Y")


def get_wind_direction(degrees):
    """
    :param degrees: direction of wind
    :return: wind direction as string
    """
    if 22.5 < degrees < 67.5: # severo vzhod
        return "SV"
    if 67.5 < degrees < 112.5:  # vzhod
        return "V"
    if 112.5 < degrees < 157.5:  # jugo vzhod
        return "JV"
    if 157.5 < degrees < 202.5:  # jugo
        return "J"
    if 202.5 < degrees < 247.5:  # jugo zahod
        return "JV"
    if 247.5 < degrees < 292.5:  # zahod
        return "Z"
    if 292.5 < degrees < 337.5:  # severo zahod
        return "SZ"
    else:
        return "S"
