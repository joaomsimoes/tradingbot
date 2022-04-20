import json
from sqlalchemy import create_engine


def db_connection():
    f = open("keys.json")
    data = json.load(f)
    engine = create_engine(data['connection'])

    return engine


def query(prod=None, values=None):
    engine = db_connection()
    connection = engine.raw_connection()
    cursor = connection.cursor()
    cursor.callproc(prod, values)
    results = list(cursor.fetchall())
    connection.commit()
    connection.close()

    return results
