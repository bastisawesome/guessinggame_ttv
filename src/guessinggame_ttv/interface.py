'''
Note: Once added, words cannot be changed through the interface.
'''

from __future__ import annotations

import logging
import enum

from typing import Tuple
from types import TracebackType

from consolemenu import ConsoleMenu, SelectionMenu
from consolemenu.items import SubmenuItem, FunctionItem
from consolemenu.screen import Screen
from consolemenu.prompt_utils import PromptUtils, UserQuit

from guessinggame_ttv.database import (DatabaseManager, RedeemExistsException,
                                       WordExistsException)


class UserInputCode(enum.Enum):
    MissingValue = enum.auto()
    IncorrectType = enum.auto()


class UserInputError(Exception):
    def __init__(self, key: str, msg: str, code: UserInputCode):
        self.key = key
        self.msg = msg
        self.code = code

        super().__init__()


class Interface:
    def __init__(self, databasemanager: DatabaseManager):
        """Interface object that allows the user to configure the bot.

        Args:
            databasemanager (DatabaseManager):
                Allows the interface to communicate with the Sqlite3 database.
        """

        self.logger = logging.getLogger('guessinggame_ttv')

        self.logger.info('Initialising interface')

        self.main_menu = ConsoleMenu(
            'GuessingGame_TTV Configuration Menu',
            'Warning: Do not use while the bot is running, data may be lost.'
        )

        self.redeems_menu = ConsoleMenu(
            'Redeems Menu'
        )

        self.wordlist_menu = ConsoleMenu(
            'Wordlist Menu'
        )

        self.databasemanager = databasemanager

        self._init_main_menu()
        self._init_redeems_menu()
        self._init_wordlist_menu()

        self.prompt_util = PromptUtils(Screen())

    def _init_main_menu(self) -> None:
        self.logger.info('Initialising the main menu')

        redeems_smitem = SubmenuItem(
            'Manage Redeems',
            self.redeems_menu,
            self.main_menu
        )
        wordlist_smitem = SubmenuItem(
            'Manage Wordlist',
            self.wordlist_menu,
            self.main_menu
        )

        self.logger.info('Adding items to main menu')

        self.main_menu.append_item(redeems_smitem)
        self.main_menu.append_item(wordlist_smitem)

    def _init_redeems_menu(self) -> None:
        self.logger.info('Initialising the redeems menu')

        add_item = FunctionItem('Add Redeem', self.add_redeem)
        modify_item = FunctionItem('Modify Existing Redeem', self.modify_redeem)
        remove_item = FunctionItem('Remove Redeem', self.remove_redeem)

        self.logger.info('Adding items to redeems menu')

        self.redeems_menu.append_item(add_item)
        self.redeems_menu.append_item(modify_item)
        self.redeems_menu.append_item(remove_item)

    def _init_wordlist_menu(self) -> None:
        self.logger.info('Initialising the wordlist menu')

        add_to_wordlist = FunctionItem(
            'Add To Existing Wordlist',
            self.add_to_wordlist
        )

        wipe_wordlist = FunctionItem(
            'Wipe Existing Wordlist',
            self.wipe_wordlist
        )

        self.logger.info('Adding items to wordlist menu')

        self.wordlist_menu.append_item(add_to_wordlist)
        self.wordlist_menu.append_item(wipe_wordlist)

    def prompt(self, prompt: str, default: str | None = None) -> str | None:
        """Displays a custom prompt to the user.

        Args:
            prompt (str): Message displayed to the user.
            default (str | None, optional):
                Default value of the prompt. When supplied, allows the user to
                enter nothing to use the default value. Defaults to None.

        Returns:
            str | None: The value supplied by the user as a string, or nothing
                        if the user cancels out of the prompt.
        """

        try:
            result = self.prompt_util.input(
                prompt,
                default=default,
                enable_quit=True,
                quit_message='(q to cancel)'
            ).input_string.strip()
        except (UserQuit, EOFError):
            self.logger.info('User cancelled out of prompt')
            return None

        return result

    def notify(self, message: str) -> None:
        """Displays a message to the user.

        Args:
            message (str): Message to display.
        """

        try:
            self.prompt_util.enter_to_continue(message+' [Enter to continue]')
        except EOFError:
            # Exists to prevent printing an exception on EOF signal.
            pass

    def prompt_redeem_info(self, default: str | None = None) -> Tuple[str, int]:
        """Collects information about a custom redeem.

        Displays a prompt to the user to get the name and cost of a custom
        redeem. Can be used either to create a new redeem or modify an existing
        redeem.

        Raises multiple exceptions on input validation, depending on the cause
        of invalid inputs (see below).

        Args:
            default (str | None, optional):
                If available, shows a default redeem name. Defaults to None.

        Raises:
            UserInputError:
                An exception on validating user input. Provides the name of the
                variable being assigned to, a detailed message about what went
                wrong, and the error code associated with the exception.

        Returns:
            Tuple[str, int]: Tuple with the redeem name and cost.

        Todo:
            Make return a named tuple
        """
        redeem_name = self.prompt('Name of redeem', default=default)

        if not redeem_name or not redeem_name.strip():
            self.logger.info('Redeem name was blank, raising exception')

            raise UserInputError(
                'redeem_name',
                'Name was not provided',
                UserInputCode.MissingValue
            )

        redeem_cost_str = self.prompt('Cost of redeem')

        if not redeem_cost_str:
            self.logger.info('Redeem cost was blank, raising exception')

            raise UserInputError(
                'redeem_cost',
                'Redeem cost was not provided',
                UserInputCode.MissingValue
            )

        if not redeem_cost_str.isdecimal() or int(redeem_cost_str) < 1:
            self.logger.info(
                'Redeem cost was not an int or is less than 0 , '
                'raising exception'
            )

            raise UserInputError(
                'redeem_cost',
                'Redeem cost was not an integer',
                UserInputCode.IncorrectType
            )

        return (redeem_name, int(redeem_cost_str))

    def add_redeem(self) -> None:
        """Prompts for redeem info and adds redeem to database."""

        self.logger.info('User adding a redeem')

        try:
            redeem_name, redeem_cost = self.prompt_redeem_info()
        except UserInputError as e:
            match e:
                case UserInputError(key='redeem_name'):
                    self.notify('Redeem name is required, please try again')
                case UserInputError(
                    key='redeem_cost',
                    code=UserInputCode.MissingValue
                ):
                    self.notify('Redeem cost is required, please try again')
                case UserInputError(
                    key='redeem_cost',
                    code=UserInputCode.IncorrectType
                ):
                    self.notify('Cost must be a whole number above 0')
        else:
            try:
                self.databasemanager.add_redeem(
                    redeem_name, redeem_cost)
            except RedeemExistsException:
                self.logger.info(
                    'Redeem already in database, notifying'
                )

                self.notify(
                    'Redeem is already in the database, '
                    'consider modifying the redeem or try again.'
                )
            else:
                self.logger.info('New redeem added to database')

                self.notify('Redeem successfully added!')

        self.logger.info('Returning to main menu')

    def modify_redeem(self) -> None:
        """Creates a menu and modifies an existing redeem in the database."""

        self.logger.info('Modifying an existing redeem')

        redeem = self._get_redeem_from_selection('Select Redeem to Modify')

        if not redeem:
            self.logger.info('User chose to quit out of menu')

            return

        try:
            new_name, new_cost = self.prompt_redeem_info(default=redeem)
        except UserInputError as e:
            match e:
                case UserInputError(key='redeem_name'):
                    self.notify('Redeem name is required, please try again')
                case UserInputError(
                    key='redeem_cost',
                    code=UserInputCode.MissingValue
                ):
                    self.notify('Redeem cost is required, please try again')
                case UserInputError(
                    key='redeem_cost',
                    code=UserInputCode.IncorrectType
                ):
                    self.notify('Cost must be a whole number above 0')
        else:
            self.databasemanager.modify_redeem(redeem, new_name, new_cost)

            self.notify('Redeem successfully edited!')

        self.logger.info('Returning to main menu')

    def _get_redeem_from_selection(self, msg: str) -> str | None:
        self.logger.info('Creating selection menu')

        redeem_list = self.databasemanager.get_all_redeems()

        options = [f'{name}: {cost}' for name,
                   cost in [redeem for redeem in redeem_list]]

        selection = SelectionMenu.get_selection(options, msg)

        try:
            self.logger.info('Attempting to return user selection')

            return redeem_list[selection][0]
        except IndexError:
            self.logger.info('User either chose to quit')

            return None

    def remove_redeem(self) -> None:
        """Creates a menu and removes a redeem from the database."""

        self.logger.info('Removing an existing redeem')

        redeem = self._get_redeem_from_selection('Select Redeem to Remove')

        if not redeem:
            self.logger.info('Assuming user wants to quit out of menu')

            return

        self.databasemanager.remove_redeem(redeem)

        self.logger.info('Redeem removed from database')

        self.logger.info('Returning to main menu')

    def add_to_wordlist(self) -> None:
        """Adds multiple words to a category in the database."""

        self.logger.info('Adding word to wordlist')

        try:
            cont = self.prompt_util.prompt_for_yes_or_no(
                'This option will change the current word value'
            )
        except EOFError:
            self.logger.info('User chose to quit')

        if not cont:
            self.logger.info('User chose to quit')

            return

        category = self.prompt('Enter category')

        if not category:
            self.logger.info('User input invalid category, notifying')

            self.notify('Category is required, please try again')

            return
        delim = self.prompt_util.input(
            'Enter delimiter', default='Enter').input_string

        if not delim:
            self.logger.info('User sent EOF signal, assuming quit condition')

        if delim == 'Enter':
            delim = '\n'
            self.notify(
                'Submit the new wordlist by pressing Enter on a blank line')
        else:
            self.notify('Submit the new wordlist by pressing Enter')

        wordlist: list[str] = []

        self.logger.info('Preparing to read from wordlist')

        if delim == '\n':
            try:
                while word := self.prompt_util.input('').input_string.strip():
                    wordlist.append(word)
            except EOFError:
                # Allow the user to also use CTRL+D (Linux) CTRL+Z+Enter
                # (Windows) to submit the wordlist
                pass
        else:
            words_in = self.prompt_util.input('').input_string.strip()
            wordlist = words_in.split(delim)

        if not wordlist:
            self.logger.info('Empty wordlist, notifying')

            self.notify('Wordlist cannot be empty, please try again')

        self.logger.info('Adding wordlist to database.')

        try:
            self.databasemanager.add_words(wordlist, category)
            self.databasemanager.set_meta('round_end', 'False')
            self.databasemanager.set_meta('update_round', 'True')
        except WordExistsException:
            self.logger.info('User input duplicate word, notifying')

            self.notify(
                'One or more words already in database, no changes made')
            return

        self.logger.info('Successfully added new words to database')

    def wipe_wordlist(self) -> None:
        """Deletes the wordlist from the database."""

        self.logger.info('User requested to wipe the wordlist')

        if not self.databasemanager.get_words():
            self.logger.info('No wordlist to wipe, notifying')

            self.notify('Wordlist has not been assigned, nothing to be done')
            return

        if not self.prompt_util.prompt_for_yes_or_no(
            'This will completely wipe the wordlist and end the current '
                'round. Are you sure you want to continue?'):

            self.logger.info('Wordlist wipe cancelled')

            return

        self.databasemanager.set_wordlist({})
        self.databasemanager.set_meta('round_end', 'True')
        self.databasemanager.set_meta('distribute_points', 'True')

        self.logger.info('Wiped the current wordlist, returning to previous '
                         'menu')

    def __enter__(self) -> Interface:
        return self

    def __exit__(self, exc_type: type[BaseException] | None,
                 exc_value: BaseException | None,
                 traceback: TracebackType) -> None:
        self.logger.info('Tearing down database manager')

        self.databasemanager.teardown()

    def run(self) -> None:
        """Starts displaying and processing the interface."""

        self.main_menu.show()
