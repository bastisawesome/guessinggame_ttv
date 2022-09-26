from guessinggame_ttv.database import DatabaseManager

import logging
import pytest
import sqlite3
from Typing import Union, Tuple

logging.disable()


@pytest.fixture()
def dbmanager() -> DatabaseManager:
    return DatabaseManager(_in_memory=True)


@pytest.fixture
def dbconn() -> sqlite3.Connection:
    pass


@pytest.fixture
def dbmanagerfilled(dbmanager: DatabaseManager) -> DatabaseManager:
    # Fill database with dummy values
    conn = dbmanager._connection

    # Add two dummy categories
    values: list[Union[Tuple[str, str], str]] = ['dummy1', 'dummy2']
    conn.executemany('INSERT INTO categories (name) VALUES  (?)',
                     values)

    # Add some dummy words
    values = [('word1', 1), ('word2', 1), ('word3', 2), ('word4', 2)]
    conn.executemany('INSERT INTO wordlist (word, category_id) VALUES (?,?)',
                     values)

    # Add some dummy users
    values = [('MultiDarkSamuses', 3, 5), ('DummyUser', 4, 1)]
    conn.executemany('INSERT INTO users (username, score, tokens)'
                     'VALUES (?, ?, ?)',
                     values)

    # Add some dummy redeems
    values = [('dummyredeem1', 1), ('dummyredeem2', 10)]
    conn.executemany('INSERT INTO redeems (name, cost) VALUES (?,?)',
                     values)

    # Add some dummy metadata
    values = [('dummymetastr', 'this is dummy meta'),
              ('dummymetablob', '{"name": "test", "some_val": 1}')]
    conn.executemany('INSERT INTO meta (name, data) VALUES (?,?)',
                     values)

    return dbmanager
