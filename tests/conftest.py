from guessinggame_ttv.database import DatabaseManager

import logging
import pytest
import sqlite3

logging.disable()


@pytest.fixture(scope='function')
def dbmanager() -> DatabaseManager:
    dm = DatabaseManager(_in_memory=True)
    yield dm
    dm.teardown()
    # del dm


@pytest.fixture(scope='function')
def dbconn(dbmanager: DatabaseManager) -> sqlite3.Connection:
    # Hopefully the only statement in the entire program to need to actually
    # ignore. MyPy can't handle the type of DatabaseManager._connection from
    # this particular function.
    return dbmanager._connection  # type: ignore


@pytest.fixture(scope='function')
def dbmanagerfilled(dbmanager: DatabaseManager) -> DatabaseManager:
    # Fill database with dummy values
    conn = dbmanager._connection

    # Add two dummy categories
    cats = [('dummy1',), ('dummy2',)]
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

    yield dbmanager
    # dbmanager.teardown()
