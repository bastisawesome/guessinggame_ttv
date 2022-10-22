from guessinggame_ttv.database import (
    DatabaseManager, MetaNotFoundException, UserNotFoundException)

from typing import NamedTuple, Tuple

import random
import logging


ProcessData = NamedTuple('ProcessData',
                         [('success', bool), ('word', str),
                          ('score', int), ('words_remaining', int)])


class Game:
    def __init__(self, databasemanager: DatabaseManager):
        """Game object that controls the back-end of the game systems.

        Args:
            databasemanager (DatabaseManager): Database manager.
        """

        self.logger = logging.getLogger('guessinggame_ttv')

        self.logger.info('Initialising the game object')

        self._databasemanager = databasemanager

        self._current_word: str = ''
        self._current_point_value: int = 0
        self._current_category: str = ''
        self._running: bool = False

        try:
            self.logger.info('Checking for a round update')

            update_round = eval(self._databasemanager.get_meta('update_round'))
        except MetaNotFoundException:
            self.logger.info('No need to update the round')

            update_round = False

        try:
            self.logger.info('Checking if the previous round has ended')

            round_ended = eval(self._databasemanager.get_meta('round_end'))
        except MetaNotFoundException:
            self.logger.info(
                'Round end not in database, setting running to true')

            round_ended = False

        if round_ended:
            self.logger.info('Round ended, not running the game module')

            self._running = False

            try:
                self.logger.info(
                    'Checking to see if points need to be distributed')

                distribute_points = eval(self._databasemanager.get_meta(
                    'distribute_points'))
            except MetaNotFoundException:
                self.logger.info('Distribute points not found in database')

                distribute_points = False

            if distribute_points:
                self.logger.info('Distributing points')
                self.end_round()

            self.logger.info('Finished initialising game, round not starting.')

            return

        self.logger.info('Preparing the game')

        loaded_data = self._load_previous_data()

        if loaded_data and update_round:
            self.logger.info(
                'Loaded data, round has changed so recalculating point value')
            self.update_point_value()
        else:
            self.logger.info('No previous data to load, setting up new round')
            chose_word = self.choose_new_word()

            if chose_word:
                self.logger.info(
                    'Word and category selected, updating point value')

                self.update_point_value()

        self.logger.info('Checking that the round can be started')

        if loaded_data or chose_word:
            self.logger.info('Round can begin')

            self._running = True
        else:
            self.logger.info('Round cannot begin')

            self._running = False

    def _load_previous_data(self) -> bool:
        try:
            self.logger.info('Querying the database for saved information')

            word = self._databasemanager.get_meta('cur_word')
            cat = self._databasemanager.get_meta('cur_cat')
            points = int(self._databasemanager.get_meta('cur_points'))
        except MetaNotFoundException:
            self.logger.info(
                'Failed to load data from database, returning false')

            return False

        self._current_word = word
        self._current_category = cat
        self._current_point_value = points

        return bool(self._current_word)

    def choose_new_word(self) -> bool:
        """Select a new word at random from the database.

        Returns:
            bool: Whether or not a word was successfully chosen.
        """

        self.logger.info('Getting wordlist from database')

        wordlist = self._databasemanager.get_words()

        if not wordlist:
            self.logger.info('No words were found, aborting')

            return False

        self.logger.info('Randomly selecting a word/category pair')

        word, cat = random.choice(wordlist)

        self._current_word = word
        self._current_category = cat

        self.logger.info('Removing word from database')
        self._databasemanager.remove_word(word)

        self.logger.info('Successfully chose a new word and category')

        return True

    def update_point_value(self) -> None:
        """Sets the current point value based on words left in the database.

        Sets the point values based on words left in database, using the
        following chart:
        - 1 point for over 20 words
        - 2 points for 11-20 words
        - 3 points for 10 or fewer words
        """
        self.logger.info('Querying the database for word count')

        num_words = self._databasemanager.get_remaining_word_count()

        if num_words > 20:
            self.logger.info('More than 20 words, point value is 1')

            self._current_point_value = 1
        elif 11 <= num_words <= 20:
            self.logger.info('11-20 words, point value is 2')

            self._current_point_value = 2
        else:
            self.logger.info('10 or fewer words, point value is 3')

            self._current_point_value = 3

    @property
    def word(self) -> str:
        """The currently selected word."""
        return self._current_word

    @property
    def point_value(self) -> int:
        """The current point value of each word."""
        return self._current_point_value

    @property
    def category(self) -> str:
        """The current word's category."""
        return self._current_category

    @property
    def running(self) -> bool:
        """Whether or not the game is currently running."""
        return self._running

    def process(self, username: str, msg: str) -> ProcessData:
        """Process message from user to see if the current word is found.

        Args:
            username (str): Name of the user who sent the message.
            msg (str): The message text.

        Returns:
            ProcessData:
                A named tuple consisting of the status, current word, current
                category, and number of remaining words.
                If the word is not in the message, current word and category are
                None.
        """
        self.logger.info(f'Processing {username}\'s message')

        # Because we remove words from the database after selecting them,
        # the total word count is off by 1. So we add 1 to account for this.
        remaining_words = self._databasemanager.get_remaining_word_count() + 1

        if self._current_word not in msg:
            self.logger.info('Current word was not in the message')
            return ProcessData(False, None, None, remaining_words)

        self.logger.info('Current word was in the message')

        cur_word = self._current_word
        cur_pv = self._current_point_value

        ret_data = ProcessData(True, cur_word, cur_pv, remaining_words-1)

        try:
            self.logger.info('Updating user information in the database')

            self._databasemanager.add_score(username, cur_pv)
        except UserNotFoundException:
            self.logger.info('User not found, creating a new user')

            self._databasemanager.add_user(username, score=cur_pv)

        if remaining_words - 1 == 0:
            self.logger.info('No words remaining')

            return ret_data

        self.logger.info('Updating round information')

        self.choose_new_word()
        self.update_point_value()

        return ret_data

    def end_round(self) -> list[Tuple[str, int]]:
        """Ends the current round.

        Returns:
            list[Tuple[str, int]]:
                Pass-through of the highscores from the database.
        """
        self.logger.info('Ending the round')

        highscore_users = self._databasemanager.get_highscores()

        self._distribute_points(highscore_users)

        self.logger.info('Update round information in the database')

        self._databasemanager.reset_scores()

        self._databasemanager.set_meta('round_end', str(True))
        self._databasemanager.set_meta('distribute_points', str(False))
        self._databasemanager.set_meta('cur_word', '')
        self._databasemanager.set_meta('cur_cat', '')
        self._databasemanager.set_meta('cur_points', '0')
        self._running = False

        return highscore_users

    def _distribute_points(self, users: list[Tuple[str, int]]) -> None:
        self.logger.info('Distributing points to highest scoring users')

        if not users:
            self.logger.info('No users scored any points')
            return

        high = users[0][1]
        low = users[-1][1]

        print(f'{high=}')
        print(f'{low=}')

        for user, score in users:
            print(f'{user=}, {score=}')
            if score == high:
                self._databasemanager.add_tokens(user, 3)
            elif score > low:
                self._databasemanager.add_tokens(user, 2)
            else:
                self._databasemanager.add_tokens(user, 1)

    def teardown(self) -> None:
        if not self._running:
            self.logger.info('Game is not running, updating database')

            self._databasemanager.set_meta('round_end', str(True))
            self._databasemanager.set_meta('distribute_points', str(False))
            self._databasemanager.set_meta('update_round', str(False))

            return

        self.logger.info(
            'Game is running, saving the current state to database')

        self._databasemanager.set_meta('cur_word', self._current_word)
        self._databasemanager.set_meta('cur_cat', self._current_category)
        self._databasemanager.set_meta(
            'cur_points', str(self._current_point_value))
        self._databasemanager.set_meta('round_end', str(False))
        self._databasemanager.set_meta('distribute_points', str(False))
        self._databasemanager.set_meta('update_round', str(False))
