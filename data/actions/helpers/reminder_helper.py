import datetime
import dateparser

import data.actions.database as database


def save_reminder(name, user_id, date_time):
    sql = (
        "INSERT INTO reminders (name, user_id, date_time)"
        "VALUES (%s, %s, %s)"
        "RETURNING id;"
    )
    data = (
        name,
        user_id,
        date_time,
    )
    return database.execute_query(sql, data)


def remove_reminder(name, user_id):
    sql = (
        "DELETE FROM reminders "
        "WHERE name = %s AND "
        "user_id = %s "
        "RETURNING id;"
    )
    data = (
        name,
        user_id,
    )
    return database.execute_query(sql, data)


def remove_reminder_by_id(reminder_id):
    sql = (
        "DELETE FROM reminders "
        "WHERE id = %s "
        "RETURNING name;"
    )
    data = (
        reminder_id,
    )
    return database.execute_query(sql, data)


def get_all_reminders(user_id):
    sql = (
        "SELECT id, name, date_time FROM reminders "
        "WHERE user_id = %s "
        "ORDER BY date_time;"
    )
    data = (
        user_id,
    )
    return database.execute_query(sql, data)


def get_reminder(user_id, reminder_name):
    sql = (
        "SELECT EXISTS (SELECT 1 FROM reminders "
        "WHERE user_id = %s AND"
        "name ILIKE %s);"
    )
    data = (
        user_id,
        reminder_name,
    )
    return database.execute_query(sql, data)


def validate_time(string_time):
    time = dateparser.parse(string_time)
    print(f"String time = {string_time} ----> validating time {time}")
    # If time is not found, tell the user how should he format it
    if time is None:
        return 1
    present = datetime.datetime.now()
    print("comparing")
    print(present, time)
    # Reminder is set in the past
    if time < present:
        return 2
    return time.strftime("%H:%M")


def validate_date(string_date):
    date = dateparser.parse(string_date, settings={'DATE_ORDER': 'DMY'}, languages=['sl'])
    print(f"String date = {string_date} ----> validating date {date}")
    # If date is not found, tell the user how should he format it
    if date is None:
        return 1
    present = datetime.datetime.combine(datetime.datetime.today(), datetime.datetime.min.time())
    # Reminder is set in the past
    print(date.strftime("%d.%m.%Y"))
    if date < present:
        return 2
    return date.strftime("%d.%m.%Y")
