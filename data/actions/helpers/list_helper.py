# import database as database
import actions.database as database
import re


def create_list(name, user_id):
    sql = (
        "INSERT INTO list (name, user_id) "
        "VALUES (%s, %s)"
        "RETURNING id;"
    )
    data = (
        name,
        user_id,
    )
    return database.execute_query(sql, data)


def remove_list(name, user_id):
    sql = (
        "DELETE FROM list "
        "WHERE name = %s AND "
        "user_id = %s "
        "RETURNING id;"
    )
    data = (
        name,
        user_id,
    )
    return database.execute_query(sql, data)


def add_to_list(list_id, item, user_id):
    item = re.sub('dodaj ', '', item, flags=re.IGNORECASE)
    sql = (
        "INSERT INTO list_items (list_id, item) "
        "VALUES (%s, %s)"
        "RETURNING id;"
    )
    data = (
        list_id,
        item,
    )
    return database.execute_query(sql, data)


def remove_from_list(list_id, item):
    sql = (
        "DELETE FROM list_items "
        "WHERE list_id = %s AND " 
        "item ILIKE %s "
        "RETURNING id;"
    )
    data = (
        list_id,
        item,
    )
    return database.execute_query(sql, data)


def remove_list_items(list_id, user_id):
    sql = (
        "DELETE FROM list_items "
        "WHERE list_id = %s AND " 
        "user_id = %s;"
    )
    data = (
        list_id,
        user_id,
    )
    return database.execute_query(sql, data)


def get_list(list_name, user_id):
    sql = (
        "SELECT * FROM list "
        "WHERE user_id = %s AND "
        "name ILIKE %s;"
    )
    data = (
        user_id,
        list_name,
    )
    return database.execute_query(sql, data)


def get_list_items(list_name):
    sql = (
        "SELECT li.item FROM list_items as li, list as l "
        "WHERE l.name = %s AND "
        "li.list_id = l.id;"
    )
    data = (
        list_name,
    )
    return database.execute_query(sql, data)


def get_all_user_lists(user_id):
    sql = (
        "SELECT name FROM list "
        "WHERE user_id = %s"
    )
    data = (
        user_id,
    )
    return database.execute_query(sql, data)