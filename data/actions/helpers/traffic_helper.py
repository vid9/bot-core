import re

import database as database
# from actions import database


def get_latest_traffic():
    sql = (
        "SELECT title, body FROM traffic;"
    )
    res = database.execute_query(sql, None)
    if not res:
        return None
    else:
        return res

# def format_traffic(title, body):
#     elements = []
#     list_element = {'title': re.sub(r'("[\s\w]*)"([\s\w]*")', r"\1\'\2", title),
#                     'subtitle': re.sub(r'("[\s\w]*)"([\s\w]*")', r"\1\'\2", body),
#                     'image_url': "https://www.nicepng.com/png/full/22-229128_warning-attention-road-sign-exclamation-mark-warning-icon.png",
#                     'default_action': {
#                         "type": "web_url",
#                         "url": "www.promet.si",
#                         "messenger_extensions": False,
#                         "webview_height_ratio": "full"},
#                     'buttons': [{
#                         "title": "Preberi več",
#                         "type": "web_url",
#                         "url": "www.promet.si",
#                     }]}
#     elements.append(list_element)
#     return elements
