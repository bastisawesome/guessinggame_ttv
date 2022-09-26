from packaging import version
from typing import Tuple

import sqlite3


class UserNotFoundException(Exception):
    pass


class RedeemExistsException(Exception):
    pass


class RedeemNotFoundException(Exception):
    pass


class WordNotFoundException(Exception):
    pass


class WordExistsException(Exception):
    pass


class DatabaseManager:
    schema_version: version.Version = version.Version('1.0.0')

    def __init__(self, _in_memory: bool = False):
        self._connection = sqlite3.connect(':memory:')

    def _init_database(self) -> None:
        pass

    def _init_users(self) -> None:
        pass

    def _init_redeems(self) -> None:
        pass

    def _init_categories(self) -> None:
        pass

    def _init_wordlist(self) -> None:
        pass

    def _init_meta(self) -> None:
        pass

    def teardown(self) -> None:
        pass

    def get_score(self, username: str) -> int:
        pass

    def reset_scores(self) -> None:
        pass

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
