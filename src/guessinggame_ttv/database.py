from contextlib import contextmanager
from packaging import version
from typing import Tuple, Generator, Optional

import sqlite3
import logging
import pathlib


@contextmanager
def sqlite_transaction(db: sqlite3.Connection) -> Generator[sqlite3.Cursor,
                                                            None, None]:
    """Creates a database cursor object protected by an explicit transaction.

    Begins a transaction and yields a SQLite3 `Cursor` object constrained to
    that transaction. In the event of an error, causes a rollback on the
    database. If there are no errors, commits all transactions and closes the
    `Cursor`.

    Args:
        db (sqlite3.Connection): Database connection to protect.

    Raises:
        err: Any `sqlite3` exceptions that were raised.

    Yields:
        Generator[sqlite3.Cursor, None, None]:
            Cursor object protected by transaction.
    """

    db.execute('BEGIN TRANSACTION')
    cur = db.cursor()
    try:
        yield cur
    except sqlite3.Error as err:
        db.rollback()
        raise err
    else:
        db.commit()
    finally:
        cur.close()


class DatabaseException(Exception):
    pass


class UserNotFoundException(DatabaseException):
    pass


class UserExistsException(DatabaseException):
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


class CategoryExistsException(DatabaseException):
    pass


class CategoryNotEmptyException(DatabaseException):
    pass


class MetaNotFoundException(DatabaseException):
    pass


class DatabaseManager:
    schema_version: version.Version = version.Version('1.0.0')

    def __init__(self, _in_memory: bool = False):
        '''Database Management object used to control the Sqlite3 database.

        Args:
            _in_memory (bool): Tells the manager to use an in-memory database,
                **only use for testing**.
        '''
        self.logger = logging.getLogger('guessinggame_ttv.databasemanager')
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
                                   uri=True,
                                   detect_types=sqlite3.PARSE_DECLTYPES,
                                   check_same_thread=False,
                                   isolation_level=None)

            self.logger.info('Connected to in-memory database')
        else:
            self.logger.info('Getting path to database')

            # Find path to database
            db_path = (pathlib.Path('./config/guessinggame_ttv.db').resolve())

            if db_path.exists():
                self.logger.info('Database found')

                # By default, assume the database does not need to be
                # initialised
                create_database = False

            conn = sqlite3.connect(db_path,
                                   detect_types=sqlite3.PARSE_DECLTYPES,
                                   check_same_thread=False,
                                   isolation_level=None)

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

        self._connection: sqlite3.Connection = conn

        if create_database:
            self.logger.info('Initialising database')

            self._init_users()
            self._init_redeems()
            self._init_categories()
            self._init_wordlist()
            self._init_meta()

        self.logger.info('Database initialised')
        self._connection.commit()

    def _table_exists(self, tablename: str) -> bool:
        exists_query = ('SELECT * FROM sqlite_master WHERE type = "table" AND '
                        f'name = "{tablename}"')

        exists = self._connection.execute(exists_query).fetchone()

        return exists is not None

    def _create_table(self, tablename: str, schema: str) -> None:
        '''Creates the table from the schema, migrating old data if exists.

        Accepts a table name and schema, then checks for a table with that name
        in the database. If it finds that table, it then grabs the old data,
        regenerates the table with the new schema, and finally puts the old data
        back in.

        Args:
            tablename (str): Name of the table to add.
            schema (str): Schema for the table.

        Raises:
            DatabaseException: Any errors with creating the table.
        '''

        self.logger.info(f'Initialising the `{tablename}` table')
        self.logger.info(f'Checking for existing `{tablename}` data')

        table_exists = self._table_exists(tablename)
        table_data: Optional[list[Tuple[str]]] = None

        if table_exists:
            self.logger.info(f'`{tablename}` exists, grabbing old data')

            table_data = self._copy_data(tablename)

            self.logger.info(f'Deleting the old `{tablename}` table')

            self._connection.execute('DROP TABLE ?', (tablename,))

        self.logger.info(f'Creating the `{tablename}` table')

        self._connection.execute(schema)

        # Migrating table data should be moved to a separate function.
        if table_data:
            self.logger.info(f'`Copying old data back to `{tablename}`')

            # TODO: This needs to grab the difference between the two schemas,
            #       then insert into the new table the shared data from the
            #       old table.

    def _init_users(self) -> None:
        self.logger.info('Initialising the `users` table')
        self.logger.info('Checking for existing `users` data')

        users_exists = self._table_exists('users')

        if users_exists:
            self.logger.info('`users` exists, no need to rebuild.')
            return

        self.logger.info('Creating the `users` table')

        schema = '''CREATE TABLE users (
    id INTEGER PRIMARY KEY NOT NULL UNIQUE,
    username TEXT NOT NULL UNIQUE COLLATE NOCASE,
    score INTEGER NOT NULL DEFAULT 0,
    tokens INTEGER NOT NULL DEFAULT 0
)'''
        self._connection.execute(schema)

        self.logger.info('Finished creating `users` table')

    def _init_redeems(self) -> None:
        self.logger.info('Initialising `redeems` table')
        self.logger.info('Checking for existing `redeems` table')

        redeems_exists = self._table_exists('redeems')

        if redeems_exists:
            self.logger.info('`redeems` exists, no need to rebuild')

            return

        self.logger.info('Creating `redeems` table')

        schema = '''CREATE TABLE redeems (
    name TEXT PRIMARY KEY NOT NULL UNIQUE COLLATE NOCASE,
    cost INTEGER NOT NULL
)'''
        self._connection.execute(schema)

        self.logger.info('Finished creating `redeems` table')

    def _init_categories(self) -> None:
        self.logger.info('Initialising `categories` table')
        self.logger.info('Checking if `categories` exists')

        cats_exists = self._table_exists('categories')

        if cats_exists:
            self.logger.info('`categories` exists, no need to rebuild')

            return

        self.logger.info('Creating `categories` table')

        schema = '''CREATE TABLE categories (
    id INTEGER PRIMARY KEY NOT NULL UNIQUE,
    name TEXT NOT NULL UNIQUE COLLATE NOCASE
)'''
        self._connection.execute(schema)

        self.logger.info('Finished creating `categories` table')

    def _init_wordlist(self) -> None:
        self.logger.info('Initialising `wordlist` table')
        self.logger.info('Checking for existing `wordlist` table')

        wordlist_exists = self._table_exists('wordlist')

        if wordlist_exists:
            self.logger.info('`wordlist` exists, no need to rebuild')

            return

        self.logger.info('Creating `wordlist` table')

        schema = '''CREATE TABLE wordlist(
    id INTEGER PRIMARY KEY NOT NULL UNIQUE,
    word TEXT NOT NULL UNIQUE COLLATE NOCASE,
    category_id INTEGER NOT NULL REFERENCES categories(id) ON DELETE RESTRICT
)'''
        self._connection.execute(schema)

        self.logger.info('Finished creating `wordlist` table')

    def _init_meta(self) -> None:
        self.logger.info('Initialising `meta` table')
        self.logger.info('Checking for existing `meta` table')

        meta_exists = self._table_exists('meta')

        if meta_exists:
            self.logger.info('`meta` exists, no need to rebuild')

            return

        self.logger.info('Creating `meta` table')

        schema = '''CREATE TABLE meta (
    id INTEGER PRIMARY KEY NOT NULL UNIQUE,
    name TEXT NOT NULL UNIQUE COLLATE NOCASE,
    data BLOB
)'''
        self._connection.execute(schema)

        self.set_meta('schema_version', str(self.schema_version))

        self.logger.info('Finished creating `meta` table')

    def teardown(self) -> None:
        """Closes the database connection

        Writes the current database schema version to the meta table in the
        database, then closes the connection to the database.
        """

        self.logger.info('Tearing down database connection')
        self.logger.info('Writing schema version to database')

        # Write schema version information to the database
        self._connection.execute('INSERT OR REPLACE INTO meta (name, data) '
                                 ' VALUES ( "schema_version", ?)',
                                 [str(self.schema_version)])

        self._connection.commit()

        self.logger.info('Closing database connection')

        self._connection.close()

    def get_score(self, username: str) -> int:
        """Gets the score of the user by username.

        Returns the score of the user by their username. If the user is not in
        the database the function returns 0.

        Args:
            username (str): Username of the user to get the score of, either in
                        Twitch format, or custom-format for YouTube usernames
                        (replace spaces with underscores). Case insensitive.

        Returns:
            int: The user's score, or 0 if the user is not in the database.
        """

        self.logger.info(f'Getting score for player {username}')

        query = 'SELECT score FROM users WHERE username = ?'
        with sqlite_transaction(self._connection) as cur:
            res: list[int] = (cur.execute(
                query, (username.lower(),)).fetchone())
        if res:
            self.logger.info('User found, returning score')

            return res[0]
        else:
            self.logger.info('User not found, returning default 0')

            return 0

    def reset_scores(self) -> None:
        """Sets all scores in the database to 0."""

        self.logger.info('Resetting scores for all users')

        query = 'UPDATE users SET score = 0'
        with sqlite_transaction(self._connection) as cur:
            cur.execute(query)

    def add_score(self, username: str, amount: int) -> None:
        """Adds the specific amount to the user's score by username.

        Args:
            username (str): Name of the user. If a Youtube username, replace
                        any spaces with an underscore. Case insensitive.
            amount (int): The amount of score points to add.

        Raises:
            UserNotFoundException: The user specified is not in the database.
        """

        self.logger.info(f'Adding to {username}\'s score')

        query = 'UPDATE users SET score = score + ? WHERE username = ?'
        with sqlite_transaction(self._connection) as cur:
            res = cur.execute(query, (amount, username))

        if res.rowcount == 0:
            self.logger.info('User not found, raising exception')

            raise UserNotFoundException()

    def get_highscores(self) -> list[Tuple[str, int]]:
        """Returns the highest scoring players.

        Queries the database for the highest scoring players with a non-zero
        score. In the event of a tie, only returns the 6 highest scoring users.

        Returns:
            list[Tuple[str, int]]: List of name/score pairs in order of their
                                   placement.
        """

        self.logger.info('Getting the high scores')

        highest_score_query = ('SELECT score FROM users ORDER BY score DESC '
                               'LIMIT 3')
        with sqlite_transaction(self._connection) as cur:
            highest_scores = cur.execute(
                highest_score_query).fetchall()

        highest_scores = [score[0] for score in highest_scores]

        highest_scores += [0] * (3 - len(highest_scores))

        query = ('SELECT username, score FROM users WHERE (score == ? OR score '
                 '== ? OR score == ?) AND score > 0 ORDER BY score DESC LIMIT '
                 '6')
        with sqlite_transaction(self._connection) as cur:
            res: list[Tuple[str, int]] = cur.execute(
                query, highest_scores).fetchall()

        return res

    def get_category(self, word: str) -> str:
        """Retrieves the specified word's category.

        Args:
            word (str): Word to get the category from.

        Raises:
            WordNotFoundException: The specified word was not found in the
                                   database.

        Returns:
            str: The category of the word specified.
        """

        self.logger.info(f'Getting the category for {word}')

        query = ('SELECT name FROM categories LEFT JOIN wordlist '
                 'ON categories.id = wordlist.category_id '
                 'WHERE wordlist.word = ?')
        with sqlite_transaction(self._connection) as cur:
            res: list[str] = cur.execute(query, (word,)).fetchone()

        if res:
            self.logger.info('Returning category')

            return res[0]
        else:
            self.logger.info('Word not in wordlist, raising exception')

            raise WordNotFoundException()

    def remove_category(self, category: str) -> None:
        self.logger.info(f'Removing {category} from database')

        try:
            with sqlite_transaction(self._connection) as cur:
                cur.execute(
                    'DELETE FROM categories WHERE name = ?', (category,))
        except sqlite3.IntegrityError:
            self.logger.error(f'{category} could not be deleted, still used by '
                              'the wordlist')

            raise CategoryNotEmptyException()

    def get_tokens(self, username: str) -> int:
        """Retrieves the number of tokens from the specified user.

        Args:
            username (str): Name of the user to query the tokens from.

        Returns:
            int: Number of tokens the user has, or 0 if the user is not found.
        """

        self.logger.info(f'Getting tokens for {username}')

        query = 'SELECT tokens FROM users WHERE username = ?'
        with sqlite_transaction(self._connection) as cur:
            res: list[int] = cur.execute(query, (username,)).fetchone()

        if res:
            self.logger.info('Username found, returning tokens')

            return res[0]
        else:
            self.logger.info('Username not found, defaulting to 0')

            return 0

    def set_tokens(self, username: str, amount: int) -> bool:
        """Sets the number of tokens a user has.

        Assigns the specified amount of tokens to a user, if the user is found.
        The amount is clamped to 0 or above.

        Args:
            username (str): Name of the user.
            amount (int): New amount of tokens to give the user.

        Raises:
            UserNotFoundException: User was not found in the database.

        Returns:
            bool: Whether or not the query was successful.
        """

        self.logger.info(f'Setting tokens for {username}')

        # Clamp the amount to 0
        amount = amount if amount > 0 else 0

        query = 'UPDATE users SET tokens = ? WHERE username = ?'
        with sqlite_transaction(self._connection) as cur:
            res = cur.execute(query, (amount, username))

        if res.rowcount == 0:
            self.logger.info('User not found, raising exception')

            raise UserNotFoundException()
        else:
            self.logger.info('User found, tokens were successfully set')

            return True

    def add_tokens(self, username: str, amount: int) -> None:
        """Adds some number of tokens to a user.

        Increases or decreases the amount of tokens the specified user has by a
        specified amount.

        Args:
            username (str): Name of user.
            amount (int): Positive number of tokens to add to user.

        Raises:
            UserNotFoundException: User was not found in the database.
        """

        self.logger.info(f'Adding tokens to {username}')

        # Ensure amount is an integer value
        amount = int(amount)

        if amount < 0:
            # Verify the amount will not go below 0
            num_tokens = self.get_tokens(username)

            if num_tokens + amount <= 0:
                self.logger.info(
                    'Amount would put user under 0, setting user\'s tokens to 0'
                )

                with sqlite_transaction(self._connection) as cur:
                    cur.execute('UPDATE users SET tokens = 0 WHERE '
                                'username = ?', (username,))
                return

        query = 'UPDATE users SET tokens = tokens + ? WHERE username = ?'
        with sqlite_transaction(self._connection) as cur:
            res = cur.execute(query, (amount, username))

        if res.rowcount == 0:
            self.logger.info('User not found, raising exception.')

            raise UserNotFoundException()

    def remove_tokens(self, username: str, amount: int) -> None:
        """Removes specified amount of tokens from user.

        Subtracts tokens from the user. Checks if the amount would put the user
        below 0 and sets the user's tokens to 0 in that case.

        Args:
            username (str): Name of user.
            amount (int): Number of tokens to remove.

        Raises:
            UserNotFoundException: The user was not found in the database.
        """

        self.logger.info(f'Removing tokens from {username}')

        self.add_tokens(username, -amount)

    def add_redeem(self, name: str, cost: int) -> None:
        """Adds redeem to the database.

        Args:
            name (str): Name of the redeem.
            cost (int): Cost of the redeem.

        Raises:
            RedeemExistsException: The redeem name is already in use.
        """

        self.logger.info(f'Adding redeem {name}')

        query = 'INSERT INTO redeems(name, cost) VALUES (?,?)'

        try:
            with sqlite_transaction(self._connection) as cur:
                cur.execute(query, (name, cost))
        except sqlite3.IntegrityError:
            self.logger.info('Redeem name already in use, raising exception')

            raise RedeemExistsException()

    def remove_redeem(self, name: str) -> None:
        """Removes redeem from the database.

        Args:
            name (str): Name of the redeem to remove

        Raises:
            RedeemNotFoundException: The redeem is not in the database.
        """

        self.logger.info(f'Removing {name} redeem from the database')

        query = 'DELETE FROM redeems WHERE name = ?'
        with sqlite_transaction(self._connection) as cur:
            res = cur.execute(query, (name,))

        if res.rowcount == 0:
            self.logger.info('Redeem not in database, raising exception')

            raise RedeemNotFoundException()

    def modify_redeem(self, name: str, new_name: str, new_cost: int) -> None:
        """Changes the name and cost of a redeem.

        Args:
            name (str): Name of the modified redeem.
            new_name (str): New name for the redeem.
            new_cost (int): New cost for the redeem.

        Raises:
            RedeemNotFoundException: The redeem is not in the database.
        """

        self.logger.info(f'Modifying redeem {name}')

        query = 'UPDATE redeems SET name = ?, cost = ? WHERE name = ?'
        with sqlite_transaction(self._connection) as cur:
            res = cur.execute(query, (new_name, new_cost, name))

        if res.rowcount == 0:
            self.logger.info('Redeem not in database, raising exception')

            raise RedeemNotFoundException()

    def migrate_user(self, old_username: str, new_username: str) -> None:
        """Adds the score and tokens from an old username to a new user.

        Queries the database for the score and tokens stored in an old username.
        If found, adds that score and tokens to a new user by the new username.
        Also deletes the old account from the database.

        Args:
            old_username (str): Name of the old user account.
            new_username (str): Name of the user account to migrate the data to.

        Raises:
            UserNotFoundException: Either the old or new usernames were not
                                   found.
        """

        self.logger.info(f'Migrating user {old_username}')

        get_old_data_query = ('SELECT score, tokens FROM users WHERE '
                              'username = ?')
        del_user_query = 'DELETE FROM users WHERE username = ?'
        upd_user_query = ('UPDATE users SET score = score + ?, tokens = tokens '
                          '+ ? WHERE username = ?')

        self.logger.info('Getting old user data')

        with sqlite_transaction(self._connection) as cur:
            old_data = cur.execute(
                get_old_data_query, (old_username,)).fetchone()

        if not old_data:
            self.logger.info('Previous user not found, raising exception')

            raise UserNotFoundException(old_username)

        with sqlite_transaction(self._connection) as cur:
            status = cur.execute('SELECT * FROM users WHERE username = '
                                 '?', (new_username,)).fetchone()

        if not status:
            self.logger.info('New user not found, raising exception')

            raise UserNotFoundException(new_username)

        self.logger.info('Removing old username from the database')

        with sqlite_transaction(self._connection) as cur:
            cur.execute(del_user_query, (old_username,))

        self.logger.info('Migrating data to new username')

        with sqlite_transaction(self._connection) as cur:
            cur.execute(upd_user_query, (old_data[0], old_data[1],
                                         new_username))

    def get_remaining_word_count(self) -> int:
        """Retrieves the number of words remaining."""

        self.logger.info('Getting the number of remaining words.')

        query = 'SELECT COUNT(word) FROM wordlist'
        with sqlite_transaction(self._connection) as cur:
            num_words: int = cur.execute(query).fetchone()[0]

        return num_words

    def remove_word(self, word: str) -> None:
        """Removes a word from the word list.

        Attempts to remove a word from the database. If it is the last word
        assigned to the category, also removes the category.

        Args:
            word (str): Word to be removed.

        Raises:
            WordNotFoundException: Word not found in database.
        """

        self.logger.info(f'Removing {word} from database')

        category = self.get_category(word)

        query = 'DELETE FROM wordlist WHERE word = ?'
        with sqlite_transaction(self._connection) as cur:
            result = cur.execute(query, (word,))

        if result.rowcount == 0:
            self.logger.info('Word not found in database, raising exception')

            raise WordNotFoundException()

        self.logger.info(f'Checking remaining words in the category {category}')

        with sqlite_transaction(self._connection) as cur:
            num_words = cur.execute(
                'SELECT COUNT(word) FROM wordlist LEFT JOIN categories ON '
                'category_id = categories.id WHERE categories.name = ?',
                (category,)).fetchone()[0]

        if num_words == 0:
            self.logger.info('Clearing category from database')

            self.remove_category(category)

    def get_words(self) -> list[Tuple[str, str]]:
        """Queries the database for the list of words and their categories."""

        self.logger.info('Getting the list of words and categories')

        query = ('SELECT wl.word, c.name FROM wordlist AS wl LEFT JOIN '
                 'categories AS c WHERE c.id = wl.category_id')
        with sqlite_transaction(self._connection) as cur:
            wordlist: list[Tuple[str, str]] = (cur.execute(query)
                                               .fetchall())

        return wordlist

    def add_word(self, word: str, category: str) -> None:
        """Adds word to category.

        Args:
            word (str): Word to be added.
            category (str): Category to assign word to.

        Raises:
            CategoryNotFoundException: Category not in database.
            WordExistsException: Word already in database.
        """

        self.logger.info(f'Adding {word} to database')

        cat_query = 'SELECT id FROM categories WHERE name = ?'
        word_query = 'INSERT INTO wordlist(word, category_id) VALUES (?,?)'

        with sqlite_transaction(self._connection) as cur:
            cat_id = cur.execute(cat_query, (category,)).fetchone()

        if not cat_id:
            self.logger.info('Category does not exist, raising exception')

            raise CategoryNotFoundException()

        else:
            cat_id = cat_id[0]

        try:
            with sqlite_transaction(self._connection) as cur:
                cur.execute(word_query, (word, cat_id))
        except sqlite3.IntegrityError:
            self.logger.info('Word already in database, raising exception')

            raise WordExistsException()

    def add_words(self, words: list[str], category: str) -> None:
        """Inserts new words into the database under the specified category.

        Adds a new list of words to the database. If the category is not already
        defined, also defines a new category. Raises an exception and rolls back
        the database in the event of a duplicate word being added.

        Args:
            words (list[str]): The word list to add.
            category (str): The category assigned to each word.

        Raises:
            WordExistsException: One or more words are already in the database.
        """

        self.logger.info('Adding list of words to database')

        cat_query = 'SELECT id FROM categories WHERE name = ?'
        wordlist_query = 'INSERT INTO wordlist(word, category_id) VALUES (?,?)'

        with sqlite_transaction(self._connection) as cur:
            cat_id = cur.execute(cat_query, (category,)).fetchone()

            if not cat_id:
                self.logger.info('Category does not exist, creating')

                status = cur.execute('INSERT INTO categories(name) '
                                     'VALUES (?)', (category,))
                cat_id = status.lastrowid
            else:
                cat_id = cat_id[0]

            items = [(word, cat_id) for word in words]
            try:
                self.logger.info('Inserting words into database')

                cur.executemany(wordlist_query, items)
            except sqlite3.IntegrityError:
                self.logger.info('Word already exists in database, rolling '
                                 'back and raising exception')

                raise WordExistsException()

    def set_wordlist(self, word_list: dict[str, list[str]]) -> None:
        """Replaces the existing wordlist with a new one.

        Removes the existing wordlist and categories, if they exist. Once the
        tables are empty, inserts categories into the database. There are no
        checks for pre-existing categories as Python's dictionaries don't allow
        same-keys to exist.

        After categories have been added, uses a cache of category IDs to add
        new words to the wordlist.

        Args:
            word_list (dict[str, list[str]]):
                Key-value pairing of categories and their associated list. The
                key is the name of the category, with a list of strings to
                define the words.

        Raises:
            WordExistsException: The same word exists in the wordlist.
        """

        self.logger.info('Replacing the existing wordlist')

        self.logger.info('Dropping old tables')

        try:
            with sqlite_transaction(self._connection) as cur:
                cur.execute('DELETE FROM wordlist')
                cur.execute('DELETE FROM categories')

                cat_ids: dict[str, int] = {}

                query = 'INSERT INTO categories(name) VALUES (?)'

                # While we could use Sqlite3's `executemany`, this allows us to
                # cache the category IDs, instead of needing multiple SELECT
                # queries.
                for category in word_list.keys():
                    cur.execute(query, (category,))
                    cat_ids[category] = cur.lastrowid

                self.logger.info('Creating new wordlist')

                query = 'INSERT INTO wordlist (word, category_id) VALUES (?,?)'

                for cat, words in word_list.items():
                    seq_of_params = [(word, cat_ids[cat]) for word in words]
                    cur.executemany(query, seq_of_params)
        except sqlite3.IntegrityError:
            self.logger.info('Duplicate word found, raising exception')

            raise WordExistsException()

        self.logger.info('Wordlist in database updated')

    def set_meta(self, name: str, data: str) -> None:
        """Assigns a meta row in the database.

        Args:
            name (str): Name of metadata.
            data (str): Str-formatted blob of data to be stored.
        """

        self.logger.info(f'Writing {name} to the meta table')

        query = 'INSERT OR REPLACE INTO meta(name, data) VALUES (?,?)'
        with sqlite_transaction(self._connection) as cur:
            cur.execute(query, (name, data))

    def get_meta(self, name: str) -> str:
        """Retrieves metadata from the database.

        Args:
            name (str): Metadata key.

        Raises:
            MetaNotFoundException: Metadata key not in the database.

        Returns:
            str: Metadata stored in the database.
        """

        self.logger.info(f'Getting {name} from database meta table')

        query = 'SELECT data FROM meta WHERE name = ?'
        with sqlite_transaction(self._connection) as cur:
            res: list[str] = cur.execute(query, (name,)).fetchone()

        if not res:
            self.logger.info('Meta row not found, raising exception')

            raise MetaNotFoundException()

        return res[0]

    def get_all_redeems(self) -> list[Tuple[str, int]]:
        """Retrieves all redeems and their costs from the database.

        Returns:
            list[Tuple[str, int]]: Redeem and cost pairs from the database.
        """
        self.logger.info('Getting all redeems in the database')

        query = 'SELECT name, cost FROM redeems'
        with sqlite_transaction(self._connection) as cur:
            return cur.execute(query).fetchall()

    def get_redeem_cost(self, name: str) -> int:
        self.logger.info(f'Getting cost of {name} redeem')

        query = 'SELECT cost FROM redeems WHERE name = ?'
        with sqlite_transaction(self._connection) as cur:
            res: list[int] = cur.execute(query, (name,)).fetchone()

        if not res:
            self.logger.info('Redeem not found, raising exception')

            raise RedeemNotFoundException()

        return res[0]

    def add_user(self, username: str, score: int = 0, points: int = 0) -> None:
        self.logger.info(f'Adding user {username} to the database')

        query = 'INSERT INTO users (username, score, tokens) VALUES (?, ?, ?)'

        try:
            with sqlite_transaction(self._connection) as cur:
                cur.execute(query, (username, score, points))
        except sqlite3.IntegrityError:
            self.logger.info('User already exists, raising exception')

            raise UserExistsException()

    def reset_round(self) -> None:
        """Marks round as updated and not ended."""

        self.logger.info('Resetting the round status.')

        self.set_meta('update_round', str(True))
        self.set_meta('round_end', str(False))
