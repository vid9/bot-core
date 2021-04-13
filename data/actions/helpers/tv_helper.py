import datetime as dt
import re

# import database as database
import actions.database as database


def program_name_valid(program_name):

    sql = (
        "SELECT name FROM tv_program_table "
        "WHERE name ILIKE %s;"
        # "end_time::time >= localtime;"
    )
    data = (
        program_name,
    )
    return database.execute_query(sql,data)


def get_schedule_for_program(program_name, day):
    table_name = "tv_schedule_table_" + str(day)
    sql = (
        "SELECT st.start_time, st.end_time, st.name, st.original_name, st.short_description, st.url, st.image_url, pt.name FROM {} st, tv_program_table pt "
        "WHERE pt.name ILIKE %s AND "
        "pt.id = st.program_id;"
        # "end_time::time >= localtime;"
    ).format(table_name)
    data = (
        program_name,
    )

    return database.execute_query(sql,data)


def get_currently_playing(program_name):
    time = dt.datetime.now()
    day = time.weekday()
    time = time.strftime("%H:%M:%S")
    table_name = "tv_schedule_table_" + str(day)
    sql = (
        "SELECT st.start_time, st.end_time, st.name, st.original_name, st.short_description, st.url, st.image_url, pt.name FROM {} st, tv_program_table pt "
        "WHERE pt.name ILIKE %s and "
        "st.program_id = pt.id and "
        "%s BETWEEN st.start_time and st.end_time;"
    ).format(table_name)

    data = (
        program_name,
        time,
    )
    return database.execute_query(sql, data)


def get_schedule_time_for_query(query, day):
    table_name = "tv_schedule_table_" + str(day)
    sql = (
        "SELECT st.start_time, st.end_time, st.name, st.original_name, st.short_description, st.url, st.image_url FROM {} st, tv_program_table pt "
        "WHERE st.name ILIKE %s OR "
        "st.original_name ILIKE %s;"

    ).format(table_name)
    data = (
        query,
        query
    )
    return database.execute_query(sql, data)


def get_program_schedule_for_category(program_name, category, day):
    table_name = "tv_schedule_table_" + str(day)
    time = ";"
    if day == dt.datetime.now().weekday():
        time = " AND st.end_time::time >= localtime;"
    sql = (
        "SELECT st.start_time, st.end_time, st.name, st.original_name, st.short_description, st.url, st.image_url, pt.name FROM {} st, tv_program_table pt "
        "WHERE pt.name ILIKE %s AND "
        "pt.id = st.program_id AND "
        "st.category ILIKE %s{}"
    ).format(table_name, time)

    data = (
        program_name,
        category,
        # dt.datetime.now()
    )
    return database.execute_query(sql, data)


def get_universal_schedule_for_category(category, day):
    """Get all shows for category in a day."""
    table_name = "tv_schedule_table_" + str(day)
    time = ";"
    if day == dt.datetime.now().weekday():
        time = " AND st.end_time::time >= localtime;"
    sql = (
        "SELECT st.start_time, st.end_time, st.name, st.original_name, st.short_description, st.url, st.image_url, pt.name FROM {} st, tv_program_table pt "
        "WHERE st.category ILIKE %s AND "
        "st.program_id = pt.id{}"
    ).format(table_name, time)

    data = (
        category,
    )
    return database.execute_query(sql, data)


def format_schedule(items):
    elements = []

    for show in items:
        # image = re.sub(r'\btps://', 'https://', 'banana')
        title = show[2]
        if show[3]:
            title += f" ({show[3]})"
        description = re.sub(r'("[\s\w]*)"([\s\w]*")', r"\1\'\2", show[4])
        list_element = {"title": re.sub(r'("[\s\w]*)"([\s\w]*")', r"\1\'\2", title),
                        "subtitle": f"{show[0].strftime('%H:%M')} - {show[1].strftime('%H:%M')}\n\n"
                                    f"{description}",
                        "image_url": show[6],
                        "default_action": {
                            "type": "web_url",
                            "url": show[5],
                            "messenger_extensions": False,
                            "webview_height_ratio": "full"},
                        "buttons": [{
                            "title": "Preberi več",
                            "type": "web_url",
                            "url": show[5],
                        }]}
        elements.append(list_element)
    return elements


def format_schedule_with_program(items):
    elements = []

    for show in items:
        title = show[2]
        if show[3]:
            title += f" ({show[3]})"
        description = re.sub(r'("[\s\w]*)"([\s\w]*")', r"\1\'\2", show[4])
        list_element = {"title": re.sub(r'("[\s\w]*)"([\s\w]*")', r"\1\'\2", title),
                        "subtitle": f"{show[7]}: {show[0].strftime('%H:%M')} - {show[1].strftime('%H:%M')}\n\n"
                                    f"{description}",
                        "image_url": show[6],
                        "default_action": {
                            "type": "web_url",
                            "url": show[5],
                            "messenger_extensions": False,
                            "webview_height_ratio": "full"},
                        "buttons": [{
                            "title": "Preberi več",
                            "type": "web_url",
                            "url": show[5],
                        }]}
        elements.append(list_element)
    return elements

# get_program_schedule_for_category("TV SLO 1", "Informativni", 6)
# print(format_schedule(get_universal_schedule_for_category("film".capitalize(), 4)))
# get_schedule_time_for_query("TV SLO 1", "Dnevnik", 6)
# get_currently_playing("TV SLO 1")
# get_schedule_for_program("TV SLO 1", 3)
