from guessinggame_ttv.database import (
    DatabaseManager, UserNotFoundException, WordNotFoundException)
from guessinggame_ttv.game import Game

import logging
import pytest
import sqlite3

from typing import Tuple

logging.disable()


@pytest.fixture(scope='function')
def dbmanager() -> DatabaseManager:
    dm = DatabaseManager(_in_memory=True)
    return dm


@pytest.fixture(scope='function')
def dbconn(dbmanager: DatabaseManager) -> sqlite3.Connection:
    conn: sqlite3.Connection = dbmanager._connection

    return conn


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

    return dbmanager


class DBManagerMock(DatabaseManager):
    def __init__(self) -> None:
        self.meta = {
            'update_round': 'False',
            'round_end': 'False'
        }

        self.wordlist = {
            'test_cat': ['word1', 'word2']
        }

        self.users = {
            'testuser': {
                'score': 0,
                'tokens': 0
            }
        }

        self.redeems = {
            'testRedeem': 0
        }

        self.categories = ['test_cat']

    def get_meta(self, name: str) -> str | None:
        return self.meta.get(name, None)

    def set_meta(self, name: str, value: str) -> None:
        self.meta[name] = str(value)

    def get_score(self, username: str) -> int:
        user = self.users.get(username, None)

        if user:
            return user['score']

        return 0

    def reset_scores(self) -> None:
        for user, data in self.users.items():
            data['score'] = 0

    def add_score(self, username: str, amount: int) -> None:
        try:
            self.users[username]['score'] += amount
        except KeyError:
            raise UserNotFoundException()

    def get_category(self, word: str) -> str:
        for cat, words in self.wordlist.items():
            if word in words:
                return cat
        else:
            return None

    def get_tokens(self, username: str) -> int:
        user = self.users.get(username, None)

        if user:
            return user['tokens']
        else:
            return 0

    def set_tokens(self, username: str, amount: int) -> None:
        user = self.users.get(username, None)

        if user:
            user['tokens'] = amount if amount > 0 else 0
        else:
            raise UserNotFoundException()

    def add_tokens(self, username: str, amount: int) -> None:
        user = self.users.get(username, None)

        if user:
            user['tokens'] -= amount
        else:
            raise UserNotFoundException()

    def remove_tokens(self, username: str, amount: int) -> None:
        user = self.users.get(username, None)

        if not user:
            raise UserNotFoundException()

        num_toks = user['tokens']
        final_amt = num_toks - amount

        user['tokens'] = final_amt if final_amt > 0 else 0

    def get_remaining_word_count(self) -> int:
        return len(self.words_as_list())

    def remove_word(self, word: str) -> None:
        for words in self.wordlist.values():
            if word in words:
                words.remove(word)
        else:
            raise WordNotFoundException

    def get_words(self) -> list[Tuple[str, str]]:
        out_l: list[Tuple[str, str]] = []

        for cat, words in self.wordlist.items():
            for word in words:
                out_l.append((word, cat))

        return out_l

    def words_as_list(self) -> list[str]:
        return [word for words in self.wordlist.values() for word in words]


@ pytest.fixture(scope='function')
def gameobj() -> Game:
    return Game(DBManagerMock())
