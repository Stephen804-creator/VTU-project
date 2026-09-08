import os
import sqlite3

from config.settings import settings


def get_database_path():

    path = settings.DATABASE_PATH

    directory = os.path.dirname(path)

    if directory:
        os.makedirs(
            directory,
            exist_ok=True
        )

    return path


def get_connection():

    connection = sqlite3.connect(
        get_database_path()
    )

    connection.row_factory = sqlite3.Row

    # Helps SQLite enforce relationships.
    connection.execute(
        "PRAGMA foreign_keys = ON"
    )

    return connection
