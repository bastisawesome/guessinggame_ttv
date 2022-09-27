from packaging import version
from typing import Tuple

import sqlite3
import logging
import pathlib

# Temporarily disable all logging until the logging module can be configured
logging.disable()


class DatabaseException(Exception):
    pass


class UserNotFoundException(DatabaseException):
    pass


class RedeemExistsException(DatabaseException):
    pass


class RedeemNotFoundException(DatabaseException):
    pass


class WordNotFoundException(DatabaseException):
    pass


class WordExistsException(DatabaseException):
    pass


class CategoryNotFoundException(DatabaseException):
    pass


class MetaRowNotFound(DatabaseException):
    pass


class DatabaseManager:
    schema_version: version.Version = version.Version('1.0.0')

    def __init__(self, _in_memory: bool = False):
        '''Database Management object used to control the Sqlite3 database.

        :param _in_memory: Tells the manager to use an in-memory database,
        *only use for testing*.
        '''
        self.logger = logging.getLogger('guessinggame_ttv')
        self.logger.info('Initialising DatabaseManager')
        self._init_database(_in_memory)

    def _init_database(self, _in_memory: bool) -> None:
        self.logger.info('Initialising database')

        # Flag to create the database
        create_database = True

        if _in_memory:
            self.logger.warn('Creating in-memory database, use this only for '
                             'testing')

            conn = sqlite3.connect('file:testdb?mode=memory&cache=shared',
                                   uri=True)

            self.logger.info('Connected to in-memory database')
        else:
            self.logger.info('Getting path to database')

            # Find path to database
            db_path = (pathlib.Path(__file__)
                       .joinpath('../config/guessinggame_ttv.db').resolve())

            if db_path.exists():
                self.logger.info('Database found')

                # By default, assume the database does not need to be
                # initialised
                create_database = False

            conn = sqlite3.connect(db_path)

            self.logger.info('Created connection to database on disk')

            if not create_database:
                # Check the version of the database that has been saved
                try:
                    self.logger.info('Checking database schema version')

                    data = conn.execute('SELECT data FROM meta WHERE name = '
                                        '"schema_version"').fetchone()[0]
                except sqlite3.OperationalError:
                    self.logger.info('Database had not finished initialising '
                                     'flagging to recreate')

                    # Database has not been initialised
                    create_database = True
                else:
                    # Check if the database needs to be updated
                    db_ver = version.Version(data)

                    if db_ver != self.schema_version:
                        self.logger.info('Database out of date, flagging to '
                                         'update')
                        create_database = True

        # Force Sqlite3 to validate foreign keys
        conn.execute('PRAGMA foreign_keys = 1')

        self.logger.info('Enabling Sqlite3 to validate foreign keys')

        self._connection = conn

        if create_database:
            self.logger.info('Initialising database')

            self._init_users()
            self._init_redeems()
            self._init_categories()
            self._init_wordlist()
            self._init_meta()

        self.logger.info('Database initialised')
        self._connection.commit()

    def _copy_data(self, tablename: str) -> list[Tuple[str]]:
        # Begin migrating data from the users table
        bak_name = f'{tablename}_old'
        schema = self._connection.execute('SELECT sql FROM sqlite_master '
                                          'WHERE type = "table" AND '
                                          'name = ?', [tablename]).fetchone()[0]
        schema = schema.replace(tablename, bak_name)

        self.logger.info(f'Creating backup of {tablename} table')

        self._connection.execute(schema)

        self.logger.info('Moving data to backup table')

        old_data = (self._connection.execute(f'SELECT * FROM {tablename}')
                    .fetchall())

        query = f'INSERT INTO {bak_name} VALUES ({{}})'
        filler = '?,'*len(old_data[0])

        self._connection.executemany(query.format(filler.rstrip(',')),
                                     old_data)

        return old_data

    def _table_exists(self, tablename: str) -> bool:
        exists_query = ('SELECT * FROM sqlite_master WHERE type = "table" AND '
                        f'name = "{tablename}"')
        print(exists_query)
        exists = self._connection.execute(exists_query).fetchone()

        return exists is not None

    def _init_users(self) -> None:
        self.logger.info('Initialising the `users` table')
        self.logger.info('Checking for existing `users` data')

        users_exists = self._table_exists('users')

        if users_exists:
            self.logger.info('`users` exists, backing up data')

            users_data = self._copy_data('users')

            self.logger.info('Deleting the old `users` table')

            self._connection.execute('DRP TABLE users')

        self.logger.info('Creating the `users` table')

        schema = '''CREATE TABLE users (
    id INTEGER PRIMARY KEY NOT NULL UNIQUE,
    username TEXT NOT NULL UNIQUE COLLATE NOCASE,
    score INTEGER NOT NULL DEFAULT 0,
    tokens INTEGER NOT NULL DEFAULT 0
)'''
        self._connection.execute(schema)

        if users_exists:
            self.logger.info('Copying old data back to `users` table')

            self._connection.executemany('INSERT INTO users(id, username, '
                                         'score, tokens) VALUES (?,?,?,?)',
                                         users_data)

            self.logger.info('Dropping the backup table')

            self._connection.execute('DROP TABLE users_old')

        self.logger.info('Finished creating `users` table')

    def _init_redeems(self) -> None:
        self.logger.info('Initialising `redeems` table')
        self.logger.info('Checking for existing `redeems` table')

        redeems_exists = self._table_exists('redeems')

        if redeems_exists:
            self.logger.info('`redeems` exists, backing up data')

            redeems_data = self._copy_data('redeems')

            self.logger.info('Deleting old `redeems` table')

            self._connection.execute('DROP TABLE redeems')

        self.logger.info('Creating `redeems` table')

        schema = '''CREATE TABLE redeems (
    name TEXT PRIMARY KEY NOT NULL UNIQUE COLLATE NOCASE,
    cost INTEGER NOT NULL
)'''
        self._connection.execute(schema)

        if redeems_exists:
            self.logger.info('Copying old data back into `redeems` table')

            self._connection.executemany('INSERT INTO redeems(name, cost) '
                                         'VALUES (?,?)', redeems_data)

            self.logger.info('Dropping backup table')

            self._connection.execute('DROP TABLE redeems_old')

        self.logger.info('Finished creating `redeems` table')

    def _init_categories(self) -> None:
        self.logger.info('Initialising `categories` table')
        self.logger.info('Checking if `categories` exists')

        cats_exists = self._table_exists('categories')

        if cats_exists:
            self.logger.info('`categories` exists, backing up data')

            old_data = self._copy_data('categories')

            self.logger.info('Deleting old `categories` table')

            self._connection.execute('DROP TABLE categories')

        self.logger.info('Creating `categories` table')

        schema = '''CREATE TABLE categories (
    id INTEGER PRIMARY KEY NOT NULL UNIQUE,
    name TEXT NOT NULL UNIQUE COLLATE NOCASE
)'''
        self._connection.execute(schema)

        if cats_exists:
            self.logger.info('Copying old data back into `categories` table')

            self._connection.executemany('INSERT INTO categories(id, name) '
                                         'VALUES (?,?)', old_data)

            self.logger.info('Dropping backup `categories` table')

            self._connection.execute('DROP TABLE categories_old')

        self.logger.info('Finished creating `categories` table')

    def _init_wordlist(self) -> None:
        self.logger.info('Initialising `wordlist` table')
        self.logger.info('Checking for existing `wordlist` table')

        wordlist_exists = self._table_exists('wordlist')

        if wordlist_exists:
            self.logger.info('`wordlist` exists, backing up data')

            wordlist_data = self._copy_data('wordlist')

            self.logger.info('Deleting old `wordlist` table')

            self._connection.execute('DROP TABLE wordlist_old')

        self.logger.info('Creating `wordlist` table')

        schema = '''CREATE TABLE wordlist(
    id INTEGER PRIMARY KEY NOT NULL UNIQUE,
    word TEXT NOT NULL UNIQUE COLLATE NOCASE,
    category_id INTEGER NOT NULL REFERENCES categories(id) ON DELETE RESTRICT
)'''
        self._connection.execute(schema)

        if wordlist_exists:
            self.logger.info('Copying old data back into `wordlist` table')

            self._connection.executemany('INSERT INTO wordlist(id, word, '
                                         'category_id) VALUES (?,?,?)',
                                         wordlist_data)

            self.logger.info('Dropping backup `wordlist` table')

            self._connection.execute('DROP TABLE wordlist_old')

        self.logger.info('Finished creating `wordlist` table')

    def _init_meta(self) -> None:
        self.logger.info('Initialising `meta` table')
        self.logger.info('Checking for existing `meta` table')

        meta_exists = self._table_exists('meta')

        if meta_exists:
            self.logger.info('`meta` exists, backing up data')

            meta_data = self._copy_data('meta')

            self.logger.info('Deleting old `meta` table')

            self._connection.execute('DROP TABLE `meta`')

        self.logger.info('Creating `meta` table')

        schema = '''CREATE TABLE meta (
    id INTEGER PRIMARY KEY NOT NULL UNIQUE,
    name TEXT NOT NULL UNIQUE COLLATE NOCASE,
    data BLOB
)'''
        self._connection.execute(schema)

        if meta_exists:
            self.logger.info('Copying old data back into `meta` table')

            self._connection.executemany('INSERT INTO meta (id, name, data) '
                                         'VALUES (?,?,?)', meta_data)

            self.logger.info('Dropping backup table')

            self._connection.execute('DROP TABLE meta_old')

        self.logger.info('Finished creating `meta` table')

    def teardown(self) -> None:
        self.logger.info('Tearing down database connection')
        self.logger.info('Writing schema version to database')

        # Write schema version information to the database
        self._connection.execute('INSERT OR REPLACE INTO meta (name, data) '
                                 ' VALUES ( "schema_version", ?)',
                                 [str(self.schema_version)])

        self.logger.info('Closing database connection')

        self._connection.close()

    def get_score(self, username: str) -> int:
        query = 'SELECT score FROM users WHERE username = ?'
        res: list[int] = (self._connection.execute(query, (username.lower(),))
                          .fetchone())
        print(res)
        return res[0] if res else 0

    def reset_scores(self) -> None:
        query = 'UPDATE users SET score = 0'
        self._connection.execute(query)

    def add_score(self, username: str, amount: int) -> None:
        pass

    def get_highscores(self) -> Tuple[Tuple[str, int]]:
        pass

    def get_category(self, word: str) -> str:
        pass

    def get_tokens(self, username: str) -> int:
        pass

    def set_tokens(self, username: str, amount: int) -> None:
        pass

    def add_tokens(self, username: str, amount: int) -> None:
        pass

    def remove_tokens(self, username: str, amount: int) -> None:
        pass

    def add_redeem(self, name: str, cost: int) -> None:
        pass

    def remove_redeem(self, name: str) -> None:
        pass

    def modify_redeem(self, name: str, new_name: str, new_cost: int) -> None:
        pass

    def migrate_user(self, old_username: str, new_username: str) -> None:
        pass

    def get_remaining_word_count(self) -> int:
        pass

    def remove_word(self, word: str) -> None:
        pass

    def get_words(self) -> Tuple[Tuple[str, str]]:
        pass

    def add_word(self, word: str, category: str) -> None:
        pass

    def add_words(self, words: list[str], category: str) -> None:
        pass

    def set_wordlist(self, word_list: dict[str, list[str]]) -> None:
        pass

    def set_meta(self, name: str, data: str) -> None:
        pass

    def get_meta(self, name: str) -> str:
        pass

    def get_all_redeems(self) -> Tuple[Tuple[str, int]]:
        pass

    def get_redeem_cost(self, name: str) -> int:
        pass
