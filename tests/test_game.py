'''
FIXME: Add tests for words inside other words, should fail
'''

from guessinggame_ttv.game import Game
from .conftest import DBManagerMock


def test_game_initialisation() -> None:
    game = Game(DBManagerMock())

    assert game.logger is not None
    assert game._databasemanager is not None
    assert game.running is True
    assert game.word is not None
    assert game.point_value is not None
    assert game.category is not None


def test_game_init_round_end() -> None:
    dbmanmock = DBManagerMock()
    dbmanmock.meta['round_end'] = 'True'

    game = Game(dbmanmock)

    assert game.running is False
    assert game.word == ''
    assert game.point_value == 0
    assert game.category == ''


def test__load_previous_data_none() -> None:
    dbmanmock = DBManagerMock()
    game = Game(dbmanmock)

    assert game._load_previous_data() is False


def test__load_previous_data() -> None:
    dbmanmock = DBManagerMock()
    test_meta = {
        'cur_word': 'testword',
        'cur_cat': 'testcat',
        'cur_points': '5',
    }
    dbmanmock.meta.update(test_meta)
    game = Game(dbmanmock)

    assert game._load_previous_data() is True
    assert game.word == test_meta['cur_word']
    assert game.category == test_meta['cur_cat']
    assert game.point_value == int(test_meta['cur_points'])


def test_choose_new_word(gameobj: Game) -> None:
    db: DBManagerMock = gameobj._databasemanager
    catlist = db.wordlist.keys()
    wordlist = db.words_as_list()

    # Since it randomly selects a word, we can't test specific values.
    # But we know the constraints are what is contained in the database,
    # so we test against what is in the database.
    assert gameobj.choose_new_word() is True
    assert gameobj.word in wordlist
    assert gameobj.category in catlist
    assert gameobj.word not in db.wordlist

    db.wordlist = {}

    # Test that the function properly returns False on an empty wordlist
    assert gameobj.choose_new_word() is False

    # No testing against the current word/category/point value because the
    # function does not change anything in this event, only returns false.


def test_update_point_value(gameobj: Game) -> None:
    # Prepare some extra wordlists to check against the various point values.
    # The strings in here don't matter, but they must exist.
    more_than_20 = {
        'cat': [str(i) for i in range(24)]
    }
    more_than_11 = {
        'cat': [str(i) for i in range(13)]
    }

    gameobj.update_point_value()
    assert gameobj.point_value == 3

    gameobj._databasemanager.wordlist = more_than_11
    gameobj.update_point_value()
    assert gameobj.point_value == 2

    gameobj._databasemanager.wordlist = more_than_20
    gameobj.update_point_value()
    assert gameobj.point_value == 1


def test_process_win_round_continue(gameobj: Game) -> None:
    message = f'test message that has {gameobj.word} in it.'
    user = 'testuser'

    results = gameobj.process(user, message)

    assert results.success
    assert results.word
    assert results.score
    assert results.words_remaining == 1


def test_process_win_round_end(gameobj: Game) -> None:
    db: DBManagerMock = gameobj._databasemanager
    db.wordlist = {gameobj._current_category: [gameobj._current_word]}
    message = gameobj._current_word
    user = 'testuser'

    results = gameobj.process(user, message)

    assert results.success
    assert results.word
    assert results.score
    assert results.words_remaining == 0


def test_process_lose(gameobj: Game) -> None:
    results = gameobj.process('testuser', 'no words here')

    assert not results.success
    assert results.word is None
    assert results.score is None
    assert results.words_remaining == 2


def test_end_round(gameobj: Game) -> None:
    db: DBManagerMock = gameobj._databasemanager
    db.users['testuser']['score'] = 5
    db.users['testuser2'] = {
        'score': 5,
        'tokens': 0
    }
    db.users['testuser3'] = {
        'score': 4,
        'tokens': 0
    }
    db.users['testuser4'] = {
        'score': 3,
        'tokens': 0
    }

    gameobj.end_round()

    assert db.users['testuser']['score'] == 0
    assert db.users['testuser']['tokens'] == 3

    assert db.users['testuser2']['score'] == 0
    assert db.users['testuser2']['tokens'] == 3

    assert db.users['testuser3']['score'] == 0
    assert db.users['testuser3']['tokens'] == 2

    assert db.users['testuser4']['score'] == 0
    assert db.users['testuser4']['tokens'] == 1


def test_teardown_running(gameobj: Game) -> None:
    db: DBManagerMock = gameobj._databasemanager

    gameobj.teardown()

    meta = db.meta

    assert gameobj._current_word == meta['cur_word']
    assert gameobj._current_category == meta['cur_cat']
    assert gameobj._current_point_value == int(meta['cur_points'])
    assert meta['round_end'] == 'False'
    assert meta['update_round'] == 'False'
    assert meta['distribute_points'] == 'False'


def test_teardown_not_running(gameobj: Game) -> None:
    db: DBManagerMock = gameobj._databasemanager

    gameobj._running = False
    gameobj.teardown()

    meta = db.meta

    assert meta.get('cur_word') is None
    assert meta.get('cur_cat') is None
    assert meta.get('cur_points') is None
    assert meta['round_end'] == 'True'
    assert meta['update_round'] == 'False'
    assert meta['distribute_points'] == 'False'