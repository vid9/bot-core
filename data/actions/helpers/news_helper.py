import re
import data.actions.database as database


def get_latest_news():
    sql = (
        "SELECT title, summary, link, photo FROM news_rtv "
        "ORDER BY id;"
    )
    res = database.execute_query(sql, None)
    if not res:
        return None
    else:
        return res


def get_latest_news_by_category(category):
    sql = (
        "SELECT title, summary, link, photo FROM news_rtv "
        "WHERE category ILIKE %s OR "
        "sub_category ILIKE %s OR "
        "sub_sub_category ILIKE %s "
        "ORDER BY id;"
    )
    data = (
        category,
        category,
        category,
    )
    res = database.execute_query(sql, data)
    if not res:
        return None
    else:
        return res


def get_top_news():
    sql = (
        "SELECT rtv.title, rtv.summary, rtv.link, rtv.photo FROM news_rtv as rtv, top_news as top "
        "WHERE top.guid = rtv.guid "
        "ORDER BY top.id;"
    )
    res = database.execute_query(sql, None)
    if not res:
        return None
    else:
        return res


def save_news_subscription(name, user_id, date_time):
    sql = (
        "INSERT INTO news_subscribe (name, user_id, date_time)"
        "VALUES (%s, %s, %s) "
        "RETURNING id;"
    )
    data = (
        name,
        user_id,
        date_time,
    )
    return database.execute_query(sql, data)


def check_user_subscription(user_id):
    sql = (
        "SELECT id FROM news_subscribe "
        "WHERE user_id = %s;"
    )
    data = (
        user_id,
    )
    return database.execute_query(sql, data)


def remove_news_subscription(name, user_id):
    sql = (
        "DELETE FROM news_subscribe "
        "WHERE name = %s AND "
        "user_id = %s;"
    )
    data = (
        name,
        user_id,
    )
    return database.execute_query(sql, data)


def format_news(news):
    counter = 0
    elements = []

    for article in news:
        list_element = {"title": re.sub(r'("[\s\w]*)"([\s\w]*")', r"\1\'\2", article[0]),
                        "subtitle": re.sub(r'("[\s\w]*)"([\s\w]*")', r"\1\'\2", article[1]),
                        "image_url": article[3],
                        "default_action": {
                            "type": "web_url",
                            "url": article[2],
                            "messenger_extensions": False,
                            "webview_height_ratio": "full"},
                        "buttons": [{
                            "title": "Preberi več",
                            "type": "web_url",
                            "url": article[2],
                        }]}
        elements.append(list_element)
        counter += 1
        if counter > 9:
            break
    return elements