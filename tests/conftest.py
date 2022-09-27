from guessinggame_ttv.database import DatabaseManager

import logging
import pytest
import sqlite3

logging.disable()


@pytest.fixture
def dbmanager() -> DatabaseManager:
    return DatabaseManager(_in_memory=True)


@pytest.fixture
def dbconn() -> sqlite3.Connection:
    return sqlite3.connect('file:testdb?mode=memory&cache=shared', uri=True)


@pytest.fixture
def dbmanagerfilled(dbmanager: DatabaseManager) -> DatabaseManager:
    # Fill database with dummy values
    conn = dbmanager._connection

    # Add two dummy categories
    cats = ['dummy1', 'dummy2']
    conn.executemany('INSERT INTO categories (name) VALUES  (?)',
                     cats)

    # Add some dummy words
    words = [('word1', 1), ('word2', 1), ('word3', 2), ('word4', 2)]
    conn.executemany('INSERT INTO wordlist (word, category_id) VALUES (?,?)',
                     words)

    # Add some dummy users
    users = [('MultiDarkSamuses', 3, 5), ('DummyUser', 4, 1)]
    conn.executemany('INSERT INTO users (username, score, tokens)'
                     'VALUES (?, ?, ?)',
                     users)

    # Add some dummy redeems
    redeems = [('dummyredeem1', 1), ('dummyredeem2', 10)]
    conn.executemany('INSERT INTO redeems (name, cost) VALUES (?,?)',
                     redeems)

    # Add some dummy metadata
    metadata = [('dummymetastr', 'this is dummy meta'),
                ('dummymetablob', '{"name": "test", "some_val": 1}')]
    conn.executemany('INSERT INTO meta (name, data) VALUES (?,?)',
                     metadata)

    return dbmanager
