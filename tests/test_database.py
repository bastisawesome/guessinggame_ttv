import sqlite3
import pytest

from typing import Tuple
from guessinggame_ttv.database import (CategoryNotFoundException,
                                       DatabaseManager,
                                       RedeemExistsException,
                                       RedeemNotFoundException,
                                       UserNotFoundException,
                                       WordExistsException,
                                       WordNotFoundException,
                                       MetaNotFoundException,
                                       UserExistsException,
                                       CategoryNotEmptyException,
                                       sqlite_transaction)


@pytest.mark.parametrize('tablename,expschema',
                         [['users', [
                             'CREATE TABLE users',
                             'id INTEGER PRIMARY KEY NOT NULL UNIQUE',
                             'username TEXT NOT NULL UNIQUE COLLATE NOCASE',
                             'score INTEGER NOT NULL DEFAULT 0',
                             'tokens INTEGER NOT NULL DEFAULT 0'
                         ]],
                             ['redeems', [
                              'CREATE TABLE redeems',
                              'name TEXT PRIMARY KEY NOT NULL UNIQUE COLLATE '
                              'NOCASE',
                              'cost INTEGER NOT NULL'
                              ]],
                             ['categories', [
                              'CREATE TABLE categories',
                              'id INTEGER PRIMARY KEY NOT NULL UNIQUE',
                              'name TEXT NOT NULL UNIQUE COLLATE NOCASE'
                              ]],
                             ['wordlist', [
                              'CREATE TABLE wordlist',
                              'id INTEGER PRIMARY KEY NOT NULL UNIQUE',
                              'word TEXT NOT NULL UNIQUE COLLATE NOCASE',
                              'category_id INTEGER NOT NULL REFERENCES '
                              'categoriesid ON DELETE RESTRICT'
                              ]],
                             ['meta', [
                              'CREATE TABLE meta',
                              'id INTEGER PRIMARY KEY NOT NULL UNIQUE',
                              'name TEXT NOT NULL UNIQUE COLLATE NOCASE',
                              'data BLOB'
                              ]]])
def test_db_initialisation(dbmanager: DatabaseManager,
                           tablename: str,
                           expschema: list[str]) -> None:
    cur = dbmanager._connection.cursor()
    schema: str = (cur.execute('SELECT sql FROM sqlite_master WHERE type = '
                               '"table" and name = ?', [tablename])
                   .fetchone()[0].lower())

    # Remove unnecessary symbols from the schema
    schema = schema.replace('(', '')
    schema = schema.replace(')', '')
    schema = schema.replace(';', '')
    schema = schema.replace(',', '')

    for line in expschema:
        assert line.lower() in schema
        schema = schema.replace(line.lower(), '')

    # Check that the schema exactly matches the expected schema
    schema = schema.strip()

    assert schema == ''


@pytest.mark.parametrize('username,expected',
                         [('multidarksamuses', 3), ('dummyuser', 4),
                          ('InvalidUser', 0)])
def test_get_scores(dbmanagerfilled: DatabaseManager, username: str,
                    expected: int) -> None:
    score = dbmanagerfilled.get_score(username)
    assert score == expected


def test_reset_scores(dbmanagerfilled: DatabaseManager,
                      dbconn: sqlite3.Connection) -> None:
    dbmanagerfilled.reset_scores()
    # dbmanagerfilled.teardown()
    results = dbconn.execute('SELECT username, score FROM users').fetchall()

    assert results == [('MultiDarkSamuses', 0), ('DummyUser', 0)]


@pytest.mark.parametrize('username,add_score,expected',
                         [('multidarksamuses', 4, 7),
                          ('DummyUser', 1, 5)])
def test_add_score(dbmanagerfilled: DatabaseManager, dbconn: sqlite3.Connection,
                   username: str, add_score: int, expected: int) -> None:
    dbmanagerfilled.add_score(username, add_score)
    res = dbconn.execute('SELECT score FROM users WHERE username = ?',
                         [username]).fetchone()[0]

    assert res == expected


def test_add_score_invalid(dbmanagerfilled: DatabaseManager) -> None:
    with pytest.raises(UserNotFoundException):
        dbmanagerfilled.add_score('InvalidUser', 0)


def test_get_highscores_empty(dbmanager: DatabaseManager) -> None:
    scores = dbmanager.get_highscores()
    assert len(scores) == 0


def test_get_highscores(dbmanagerfilled: DatabaseManager) -> None:
    scores = dbmanagerfilled.get_highscores()
    comparison = [('DummyUser', 4), ('MultiDarkSamuses', 3)]

    for t in scores:
        assert t in comparison
        # Ensure that scores are EXACTLY the same
        assert not t not in comparison


def test_get_highscores_tied(dbmanagerfilled: DatabaseManager,
                             dbconn: sqlite3.Connection) -> None:
    dbconn.executemany('INSERT INTO users (username, score) VALUES (?,50)',
                       [('dummyuser2',), ('dummyuser3',), ('dummyuser4',),
                        ('dummyuser5',), ('dummyuser6',), ('dummyuser7',),
                        ('dummyuser8',)])
    scores = dbmanagerfilled.get_highscores()

    assert len(scores) == 6
    comparison = [('dummyuser2', 50), ('dummyuser3', 50), ('dummyuser4', 50),
                  ('dummyuser5', 50), ('dummyuser6', 50), ('dummyuser7', 50)]

    for score in scores:
        assert score in comparison
        # Ensure the scores are EXACTLY the same
        assert not score not in comparison


@pytest.mark.parametrize('word,expected', [('word1', 'dummy1'),
                                           ('word2', 'dummy1'),
                                           ('word3', 'dummy2'),
                                           ('word4', 'dummy2')])
def test_get_category(dbmanagerfilled: DatabaseManager,
                      word: str, expected: str) -> None:
    category = dbmanagerfilled.get_category(word)

    assert category == expected


def test_get_category_invalid(dbmanagerfilled: DatabaseManager) -> None:
    with pytest.raises(WordNotFoundException):
        dbmanagerfilled.get_category('invalidword')


def test_remove_category(dbmanagerfilled: DatabaseManager,
                         dbconn: sqlite3.Connection) -> None:
    dbmanagerfilled.remove_category('empty_category')
    none_cat = dbconn.execute('SELECT name FROM categories WHERE name = '
                              '"empty_category"').fetchone()

    assert none_cat is None


def test_remove_category_invalid(dbmanagerfilled: DatabaseManager) -> None:
    with pytest.raises(CategoryNotEmptyException):
        dbmanagerfilled.remove_category('dummy1')


@pytest.mark.parametrize('username,expected', [('MultiDarkSamuses', 5),
                                               ('DummyUser', 1),
                                               ('InvalidUser', 0)])
def test_get_tokens(dbmanagerfilled: DatabaseManager, username: str,
                    expected: int) -> None:
    tokens = dbmanagerfilled.get_tokens(username)

    assert tokens == expected


@pytest.mark.parametrize('username,amount', [('MultiDarkSamuses', 5),
                                             ('DummyUser', 2)])
def test_set_tokens(dbmanagerfilled: DatabaseManager,
                    dbconn: sqlite3.Connection, username: str,
                    amount: int) -> None:
    dbmanagerfilled.set_tokens(username, amount)
    tokens = dbconn.execute('SELECT tokens FROM users WHERE username = ?',
                            [username]).fetchone()[0]

    assert tokens == amount


def test_set_tokens_invalid(dbmanagerfilled: DatabaseManager,
                            dbconn: sqlite3.Connection) -> None:
    with pytest.raises(UserNotFoundException):
        dbmanagerfilled.set_tokens('invalid_user', 100)

    dbmanagerfilled.set_tokens('MultiDarkSamuses', -1)
    tokens = dbconn.execute('SELECT tokens FROM users WHERE username = '
                            '"MultiDarkSamuses"').fetchone()[0]

    assert tokens == 0


def test_add_tokens(dbmanagerfilled: DatabaseManager,
                    dbconn: sqlite3.Connection) -> None:
    dbmanagerfilled.add_tokens('MultiDarkSamuses', 4)
    tokens = dbconn.execute('SELECT tokens FROM users WHERE username = '
                            '"MultiDarkSamuses"').fetchone()[0]

    assert tokens == 9


def test_add_tokens_lte_zero(dbmanagerfilled: DatabaseManager,
                             dbconn: sqlite3.Connection) -> None:
    dbmanagerfilled.add_tokens('MultiDarkSamuses', -5)
    tokens = dbconn.execute('SELECT tokens FROM users WHERE username = '
                            '"multidarksamuses"').fetchone()[0]

    assert tokens == 0


def test_add_tokens_invalid(dbmanagerfilled: DatabaseManager) -> None:
    with pytest.raises(UserNotFoundException):
        dbmanagerfilled.add_tokens('InvalidUser', 1)


@pytest.mark.parametrize('username,amount,expected',
                         [('MultiDarkSamuses', 3, 2),
                          ('DummyUser', 1, 0),
                          ('MultiDarkSamuses', 70, 0)])
def test_remove_tokens(dbmanagerfilled: DatabaseManager,
                       dbconn: sqlite3.Connection, username: str, amount: int,
                       expected: int) -> None:
    dbmanagerfilled.remove_tokens(username, amount)
    res = dbconn.execute('SELECT tokens FROM users WHERE username = ?',
                         [(username)]).fetchone()[0]

    assert res == expected


def test_remove_tokens_invalid(dbmanagerfilled: DatabaseManager) -> None:
    with pytest.raises(UserNotFoundException):
        dbmanagerfilled.remove_tokens('InvalidUser', 0)


@pytest.mark.parametrize('name,cost', [('newred1', 5), ('newred2', 10)])
def test_add_redeem(dbmanagerfilled: DatabaseManager,
                    dbconn: sqlite3.Connection, name: str, cost: int) -> None:
    dbmanagerfilled.add_redeem(name, cost)
    res = dbconn.execute('SELECT name, cost FROM redeems WHERE name = ?',
                         [name]).fetchone()

    assert res == (name, cost)


def test_add_redeem_duplicate(dbmanagerfilled: DatabaseManager) -> None:
    with pytest.raises(RedeemExistsException):
        dbmanagerfilled.add_redeem('dummyredeem1', 0)


def test_remove_redeem(dbmanagerfilled: DatabaseManager,
                       dbconn: sqlite3.Connection) -> None:
    dbmanagerfilled.remove_redeem('dummyredeem2')
    res = dbconn.execute('SELECT * FROM redeems WHERE name = ?',
                         ['dummyredeem2']).fetchone()

    assert res is None


def test_remove_redeem_invalid(dbmanagerfilled: DatabaseManager) -> None:
    with pytest.raises(RedeemNotFoundException):
        dbmanagerfilled.remove_redeem('InvalidRedeem')


def test_modify_redeem(dbmanagerfilled: DatabaseManager,
                       dbconn: sqlite3.Connection) -> None:
    dbmanagerfilled.modify_redeem('dummyredeem1', 'renamedredeem', 40)
    res1 = dbconn.execute('SELECT name, cost FROM redeems WHERE name = ?',
                          ['renamedredeem']).fetchone()
    res2 = (dbconn.execute('SELECT * FROM redeems WHERE name = "dummyredeem1"')
            .fetchone())

    assert res1 == ('renamedredeem', 40)
    assert res2 is None


def test_modify_redeem_invalid(dbmanagerfilled: DatabaseManager) -> None:
    with pytest.raises(RedeemNotFoundException):
        dbmanagerfilled.modify_redeem('InvalidRedeem', 'NewInvalidRedeem', 2)


def test_migrate_user(dbmanagerfilled: DatabaseManager,
                      dbconn: sqlite3.Connection) -> None:
    dbmanagerfilled.migrate_user('DummyUser', 'MultiDarkSamuses')
    res1 = dbconn.execute('SELECT username, score, tokens FROM users WHERE '
                          'username = "MultiDarkSamuses"').fetchone()
    res2 = (dbconn.execute('SELECT * FROM users WHERE username = "DummyUser"')
            .fetchone())

    assert res1 == ('MultiDarkSamuses', 7, 6)
    assert res2 is None


@pytest.mark.parametrize('old_username,new_username',
                         [['InvalidUser', 'NewInvalidUser'],
                          ['DummyUser', 'MoreInvalidUsers']])
def test_migrate_user_invalid(dbmanagerfilled: DatabaseManager,
                              old_username: str, new_username: str) -> None:
    with pytest.raises(UserNotFoundException):
        dbmanagerfilled.migrate_user(old_username, new_username)


def test_get_remaining_word_count(dbmanagerfilled: DatabaseManager,
                                  dbconn: sqlite3.Connection) -> None:
    num_words = dbmanagerfilled.get_remaining_word_count()

    assert num_words == 4

    dbconn.execute('DELETE FROM wordlist')
    num_words = dbmanagerfilled.get_remaining_word_count()

    assert num_words == 0


def test_remove_word(dbmanagerfilled: DatabaseManager,
                     dbconn: sqlite3.Connection) -> None:
    dbmanagerfilled.remove_word('word3')
    res = dbconn.execute('SELECT word FROM wordlist').fetchall()

    word_list = [word[0] for word in res]

    assert word_list == ['word1', 'word2', 'word4']


def test_remove_word_and_category(dbmanagerfilled: DatabaseManager,
                                  dbconn: sqlite3.Connection) -> None:
    dbmanagerfilled.remove_word('word1')
    dbmanagerfilled.remove_word('word2')

    none_category = dbconn.execute('SELECT name FROM categories WHERE name '
                                   '= "dummy1"').fetchone()

    assert none_category is None


def test_remove_word_invalid(dbmanagerfilled: DatabaseManager) -> None:
    with pytest.raises(WordNotFoundException):
        dbmanagerfilled.remove_word('InvalidWord')


def test_get_words(dbmanagerfilled: DatabaseManager) -> None:
    wordlist = dbmanagerfilled.get_words()

    comparison = [('word1', 'dummy1'), ('word2', 'dummy1'),
                  ('word3', 'dummy2'), ('word4', 'dummy2')]

    for word_category in wordlist:
        assert word_category in comparison
        # Ensure the lists are EXACTLY the same
        assert not word_category not in comparison


def test_add_word(dbmanagerfilled: DatabaseManager,
                  dbconn: sqlite3.Connection) -> None:
    dbmanagerfilled.add_word('NewWord', 'dummy2')
    res = (dbconn.execute('SELECT * FROM wordlist WHERE word = "NewWord"')
           .fetchone())

    assert res is not None


def test_add_word_duplicate(dbmanagerfilled: DatabaseManager) -> None:
    with pytest.raises(WordExistsException):
        dbmanagerfilled.add_word('word1', 'dummy1')


def test_add_word_missing_category(dbmanagerfilled: DatabaseManager) -> None:
    with pytest.raises(CategoryNotFoundException):
        dbmanagerfilled.add_word('word1', 'invalidcategory')


def test_add_words_old_category(dbmanagerfilled: DatabaseManager,
                                dbconn: sqlite3.Connection) -> None:
    dbmanagerfilled.add_words(['NewWord1', 'NewWord2'], 'dummy1')
    res = (dbconn.execute('SELECT word FROM wordlist LEFT JOIN categories ON '
                          'category_id = categories.id WHERE categories.name = '
                          '"dummy1"')
           .fetchall())

    words = [word[0] for word in res]

    assert {'NewWord1', 'NewWord2'}.issubset(words)


def test_add_words_new_category(dbmanagerfilled: DatabaseManager,
                                dbconn: sqlite3.Connection) -> None:
    dbmanagerfilled.add_words(['Samus', 'Sbug'], 'Metroid')
    res = dbconn.execute('SELECT word FROM wordlist LEFT JOIN categories ON '
                         'category_id = categories.id WHERE categories.name = '
                         '"Metroid"').fetchall()

    words = [word[0] for word in res]

    assert {'Samus', 'Sbug'}.issubset(words)


def test_add_words_duplicate(dbmanagerfilled: DatabaseManager) -> None:
    with pytest.raises(WordExistsException):
        dbmanagerfilled.add_words(['newword', 'word1'], 'new_category')


def test_add_words_duplicate_mixed(dbmanager: DatabaseManager,
                                   dbconn: sqlite3.Connection) -> None:
    dbconn.execute('INSERT INTO categories(name) VALUES ("testcat")')
    dbconn.execute('INSERT INTO wordlist(word, category_id) VALUES '
                   '("word1", 1)')

    with pytest.raises(WordExistsException):
        dbmanager.add_words(['newword', 'word1'], 'dummy1')
        newword_exists = dbconn.execute('SELECT * FROM wordlist WHERE word = '
                                        '"newword"').fetchone()
        assert newword_exists is None


def test_set_wordlist(dbmanagerfilled: DatabaseManager) -> None:
    new_wordlist = {'Cat1': ['Meow', 'Purr'],
                    'Cat2': ['Nuzzle', 'Pounce']}
    dbmanagerfilled.set_wordlist(new_wordlist)

    res = dbmanagerfilled.get_words()
    print(res)

    expected: list[Tuple[str, str]] = []
    for cat, words in new_wordlist.items():
        for word in words:
            expected.append((word, cat))

    assert res == expected


def test_set_wordlist_duplicate_word(dbmanager: DatabaseManager) -> None:
    new_wordlist = {'Cat1': ['Meow', 'Purr'],
                    'Cat2': ['Pounce', 'meow']}

    with pytest.raises(WordExistsException):
        dbmanager.set_wordlist(new_wordlist)

    assert dbmanager.get_words() == []


def test_set_meta(dbmanager: DatabaseManager,
                  dbconn: sqlite3.Connection) -> None:
    dbmanager.set_meta('testmeta', '10')
    res = (dbconn.execute('SELECT data FROM meta WHERE name = "testmeta"')
           .fetchone()[0])

    assert res == '10'
    assert int(res) == 10

    # Test overriding meta

    dbmanager.set_meta('testmeta', 'new data')
    res = (dbconn.execute('SELECT data FROM meta WHERE name = "testmeta"')
           .fetchone()[0])

    assert res == 'new data'


@pytest.mark.parametrize('name,expected',
                         [('dummymetastr', 'this is dummy meta'),
                          ('dummymetablob', '{"name": "test", "some_val": 1}')])
def test_get_meta(dbmanagerfilled: DatabaseManager, name: str,
                  expected: str) -> None:
    res = dbmanagerfilled.get_meta(name)

    assert res == expected


def test_get_meta_invalid(dbmanager: DatabaseManager) -> None:
    with pytest.raises(MetaNotFoundException):
        dbmanager.get_meta('InvalidMeta')


def test_get_all_redeems(dbmanagerfilled: DatabaseManager) -> None:
    res = dbmanagerfilled.get_all_redeems()

    comparison = [('dummyredeem1', 1), ('dummyredeem2', 10)]

    for redeem in res:
        assert redeem in comparison
        # Ensure the two are EXACTLY the same
        assert not redeem not in comparison


@pytest.mark.parametrize('name,expected',
                         [('dummyredeem1', 1),
                          ('DummyRedeem2', 10)])
def test_get_redeem_cost(dbmanagerfilled: DatabaseManager, name: str,
                         expected: int) -> None:
    cost = dbmanagerfilled.get_redeem_cost(name)

    assert cost == expected


def test_get_redeem_cost_invalid(dbmanagerfilled: DatabaseManager) -> None:
    with pytest.raises(RedeemNotFoundException):
        dbmanagerfilled.get_redeem_cost('InvalidRedeem')


def test_add_user(dbmanagerfilled: DatabaseManager,
                  dbconn: sqlite3.Connection) -> None:
    dbmanagerfilled.add_user('new_user')
    score, tokens = dbconn.execute('SELECT score, tokens FROM users WHERE '
                                   'username = "new_user"').fetchone()

    assert int(score) == 0
    assert int(tokens) == 0


@pytest.mark.parametrize('exp_score, exp_tokens',
                         [[5, 0],
                          [0, 7],
                          [8, 4]])
def test_add_user_prefilled(dbmanagerfilled: DatabaseManager,
                            dbconn: sqlite3.Connection,
                            exp_score: int, exp_tokens: int) -> None:
    dbmanagerfilled.add_user('new_user', exp_score, exp_tokens)
    score, tokens = dbconn.execute('SELECT score, tokens FROM users WHERE '
                                   'username = "new_user"').fetchone()

    assert int(score) == exp_score
    assert int(tokens) == exp_tokens


def test_add_user_duplicate(dbmanagerfilled: DatabaseManager) -> None:
    with pytest.raises(UserExistsException):
        dbmanagerfilled.add_user('multidarksamuses')


def test_reset_round(dbmanager: DatabaseManager,
                     dbconn: sqlite3.Connection) -> None:
    dbmanager.reset_round()

    round_end, = dbconn.execute(
        'SELECT data FROM meta WHERE name = "round_end"').fetchone()
    update_round, = dbconn.execute(
        'SELECT data FROM meta WHERE name = "update_round"').fetchone()

    assert round_end == 'False'
    assert update_round == 'True'


# SQLite transaction tests
def test_sqlite_transaction_success(dbconn: sqlite3.Connection) -> None:
    with sqlite_transaction(dbconn) as cur:
        cur.execute(
            'INSERT INTO meta (name, data) VALUES ("test_meta", "test_value")')

    name, value = dbconn.execute(
        'SELECT name, data FROM meta WHERE name = "test_meta"').fetchone()

    assert name == "test_meta"
    assert value == "test_value"


def test_sqlite_transaction_multiple_transactions(
        dbconn: sqlite3.Connection) -> None:
    query = 'INSERT INTO meta (name, data) VALUES (?,?)'
    with sqlite_transaction(dbconn) as cur:
        cur.execute(query, ['test_meta', 'test_value'])
        cur.execute(query, ['real_meta', 'real_value'])

    test, real = dbconn.execute('SELECT name, data FROM meta').fetchall()
    assert test[0] == 'test_meta'
    assert test[1] == 'test_value'
    assert real[0] == 'real_meta'
    assert real[1] == 'real_value'


def test_sqlite_transaction_error(dbconn: sqlite3.Connection) -> None:
    with pytest.raises(sqlite3.IntegrityError):
        with sqlite_transaction(dbconn) as cur:
            cur.execute('INSERT INTO meta (name, data) VALUES (?, ?)',
                        ['test_meta', 'test_value'])
            # This statement should cause a rollback
            cur.execute('INSERT INTO meta (name, data) VALUES (?, ?)',
                        ['test_meta', 'value_not_important'])

    results = dbconn.execute('SELECT name FROM meta').fetchone()

    assert results is None
