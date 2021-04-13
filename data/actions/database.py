import psycopg2


def get_connection():
    connection = psycopg2.connect(
        dbname="rasa",
        user="postgres",
        # password="ltFMnVTAVRRvvGaLkO5c",
        # host="172.17.0.1",
        password="admin",
        host="127.0.0.1",
        port="5432",
    )
    return connection


def execute_query(query, params):
    conn = get_connection()
    cursor = conn.cursor()
    result = None
    try:
        if params is not None:
            cursor.execute(query, params)
        else:
            cursor.execute(query)
        result = cursor.fetchall()
    except psycopg2.Error as e:
        raise e
    finally:
        cursor.close()
        conn.commit()
        conn.close()
        return result
