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
        get_database_path(),
        timeout=30
    )

    connection.row_factory = sqlite3.Row

    # Wait briefly for concurrent transactions instead of failing immediately.
    connection.execute("PRAGMA busy_timeout = 30000")

    # Helps SQLite enforce relationships.
    connection.execute(
        "PRAGMA foreign_keys = ON"
    )

    return connection
