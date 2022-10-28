from twitchio.ext import commands
from guessinggame_ttv.database import (
    DatabaseManager, UserNotFoundException, RedeemNotFoundException)
from guessinggame_ttv.game import Game
from guessinggame_ttv.utils import Settings

from types import TracebackType

import twitchio
import re
import enum
import logging


class BotException(Exception):
    pass


class NotEnoughParamsException(BotException):
    pass


class Permissions(enum.IntEnum):
    MODERATOR = enum.auto()
    SUBSCRIBER = enum.auto()
    VIP = enum.auto()
    TURBO = enum.auto()
    BROADCASTER = enum.auto()


def parse_params(message: str, num_params: int) -> list[str] | None:
    """Parses a message for a given number of parameters.

    Splits a message into a list based on the number of parameters specified.
    The resulting list is made of strings and is not parsed as any specific
    types. If the number of parameters is less than or equal to 0, simply
    returns the message in a list.

    Args:
        message (str): Message to parse.
        num_params (int): Number of paramters expected in the message.
        is_command (bool): Whether or not the function is called by a command.

    Raises:
        NotEnoughParamsException:
            Raised when the message does not contain the expected number of
            parameters.

    Returns:
        list[str] | None: The split message, or nothing if there is no message.
    """

    if num_params <= 0:
        # Nothing to do
        return [message]

    if not message:
        return None

    if message.find(' ') == -1:
        raise NotEnoughParamsException()

    message = message[message.find(' ')+1:]

    params = message.split(' ', num_params)

    if len(params) < num_params:
        raise NotEnoughParamsException()

    if len(params) == num_params:
        params.append('')

    return params


def parse_restream_username(message: str) -> str:
    """Returns a normalised username from platforms supported by Restream.

    Parses the username section from a Restream message and replaces all spaces
    with underscores, if they are present. This is done for YouTube support.

    Args:
        message (str): Message sent by the Restream bot.

    Returns:
        str: Normalised username with spaces replaced by underscores.
    """
    username = re.match(r'\[.*:(.*)\]', message).group(1).strip()
    return username.replace(' ', '_')


def check_permissions(chatter: twitchio.Chatter, perms: Permissions) -> bool:
    """Returns whether or not the chatter has the required permissions.

    Args:
        chatter (twitchio.Chatter): The chatter being checked.
        perms (Permissions): The permissions expected.

    Returns:
        bool: Whether or not they have the permission.
    """
    # Comparisons are included to bypass the lack of type annotations provided
    # by TwitchIO.
    match perms:
        case Permissions.MODERATOR:
            return chatter.is_mod is True
        case Permissions.SUBSCRIBER:
            return chatter.is_subscriber is True
        case Permissions.VIP:
            return chatter.is_vip is True
        case Permissions.TURBO:
            return chatter.is_turbo is True
        case Permissions.BROADCASTER:
            return chatter.is_broadcaster is True


def parse_username(username: str) -> str:
    return username.replace('@', '')


class GuessingGameBot(commands.Bot):
    def __init__(self, settings: Settings):
        """Twitch bot object that controls the bot's interactions with Twitch.

        Bot object to connect to Twitch, interact with chat, and run the word
        guessing game.

        Args:
            settings (Settings):
                Settings required for the bot to connect to Twitch.
        """

        self.logger = logging.getLogger('guessinggame_ttv.bot')

        self.logger.info('Initialising the bot')

        self.databasemanager = DatabaseManager()
        self.game = Game(self.databasemanager)

        # Used to ensure the bot does not attempt to save multiple times.
        self._saved = False

        self.logger.info('Connecting bot to Twitch')

        super().__init__(settings.token,
                         prefix=settings.prefix,
                         client_secret=settings.client_secret,
                         initial_channels=[settings.channel])

    def __enter__(self):
        return self

    def __exit__(self, exc_type: type[BaseException] | None,
                 exc_val: BaseException | None,
                 exc_tb: TracebackType | None) -> None:
        self.logger.info('Shutting down the bot')

        self.teardown()

        self.logger.info('Bot shutdown completed')

    def teardown(self) -> None:
        """Shuts down the bot, game, and database manager."""

        self.logger.info('Shutting down the game module')

        if self.game:
            self.game.teardown()
            self.game = None

        self.logger.info('Shutting down the database manager')

        if self.databasemanager:
            self.databasemanager.teardown()
            self.databasemanager = None

        self.logger.info('Saving data')

    async def event_message(self, message: twitchio.Message) -> None:
        """|coro| Handles Twitch message events.

        Scans all messages from Twitch, ignoring messages sent by this bot.
        Determines if the message is a command or a normal message. Commands are
        ignored by the game. Non-command messages are processed by the game.

        Args:
            message (twitchio.Message): Message sent to Twitch.
        """

        if message.echo:
            self.logger.debug('Ignoring bot message')

            return

        if await self.handle_commands(message):
            self.logger.debug('Processed command, not parsing for word')

            return

        if not self.game.running:
            self.logger.debug('Game is not running, not parsing messages')
            return

        # TODO: Split this off into another function

        self.logger.debug('Getting information from the message')

        user = message.author
        content = message.content
        channel = message.channel

        if user.name.lower() == 'restreambot':
            self.logger.info('Parsing username from Restream Bot message')

            username = parse_restream_username(content)
        else:
            username = user.display_name

        self.logger.debug(f'Processing message from {username}')

        success, word, score, words_remaining = self.game.process(
            username, content)

        if not success:
            self.logger.debug(f'Message by {username} did not contain the word')
            return

        self.logger.debug(f'Message by {username} contained the word')

        message = (
            f'{username} has guessed the word: {word} and earned {score} '
            'points.')
        await channel.send(message)

        if words_remaining == 0:
            await channel.send(
                'There are no words remaining, the round has ended')

            await self._end_round(channel)

    async def _end_round(self, channel: twitchio.Channel) -> None:
        highscores = self.game.end_round()

        highest: list[str] = []
        middle: list[str] = []
        lowest: list[str] = []

        highest_score = highscores[0][1]
        lowest_score = highscores[-1][1]

        first_place_points = 3
        second_place_points = 2
        third_place_points = 1

        self.logger.info('Calculating message')

        for user, score in highscores:
            if score == highest_score:
                highest.append(user)
            elif score > lowest_score:
                middle.append(user)
            else:
                lowest.append(user)

        message = ''

        self.logger.debug('Adding highest scoring users to message')

        message += self._generate_message_from_list(highest[:6])
        message += 'have ' if len(highest) != 1 else 'has '
        message += f'earned {first_place_points} tokens. '

        if middle:
            message += self._generate_message_from_list(middle)
            message += 'have ' if len(middle) != 1 else 'has '
            message += f'earned {second_place_points} tokens. '

        if lowest:
            message += self._generate_message_from_list(lowest)
            message += 'have ' if len(middle) != 1 else 'has '
            message += f'earned {third_place_points} tokens. '

        self.logger.info('Sending winner message.')

        await channel.send(message)

    def _generate_message_from_list(self, msgs: list[str]) -> str:
        if not msgs:
            return ''

        message = ''
        if len(msgs) > 2:
            for num, msg in enumerate(msgs):
                if num < (len(msgs)-1):
                    message += f'{msg}, '
                else:
                    message += f'and {msg} '
        elif len(msgs) == 2:
            message += f'{msgs[0]} and {msgs[1]} '
        else:
            message += f'{msgs[0]} '

        return message

    async def handle_commands(self, message: twitchio.Message) -> bool:
        """See base class.

        Returns:
            bool: If the message is a command.
        """

        context = await self.get_context(message)
        return await self.invoke(context)

    async def invoke(self, context: commands.Context) -> bool:
        """See base class.

        Returns:
            bool: If the command is valid and can be invoked.
        """

        if not context.prefix or not context.is_valid:
            return False

        self.run_event('command_invoke', context)
        await context.command(context)

        return True

    @commands.command()
    async def score(self, ctx: commands.Context) -> None:
        """Outputs either the caller's or a specified user's score."""

        self.logger.info('Getting user\'s score from database')

        try:
            user, _ = parse_params(ctx.message.content, 1)
            user = parse_username(user)
        except NotEnoughParamsException:
            user = ctx.author.display_name

        score = self.databasemanager.get_score(user)

        message = f'{user} has {score} point{"s" if score != 1 else ""}.'

        await ctx.send(message)

    @commands.command()
    async def tokens(self, ctx: commands.Context) -> None:
        """Outputs either the caller's or a specified user's score."""

        self.logger.info('Getting user\'s tokens from database')

        try:
            user, _ = parse_params(ctx.message.content, 1)
            user = parse_username(user)
        except NotEnoughParamsException:
            user = ctx.author.display_name

        tokens = self.databasemanager.get_tokens(user)

        message = f'{user} has {tokens} token{"s" if tokens != 1 else ""}.'

        await ctx.send(message)

    @commands.command(aliases=['highscore'])
    async def highscores(self, ctx: commands.Context) -> None:
        """Outputs the current highscores."""

        self.logger.info('Printing the highscores')

        highscores = self.databasemanager.get_highscores()

        if not highscores:
            await ctx.channel.send('No one has any points.')
            return

        highest: list[str] = []
        middle: list[str] = []
        lowest: list[str] = []
        scores: list[int] = []

        highest_score = highscores[0][1]
        lowest_score = highscores[-1][1]

        for user, score in highscores:
            if score == highest_score:
                highest.append(user)
                scores.append(score)
            elif score > lowest_score:
                middle.append(user)
                scores.append(score)
            else:
                lowest.append(user)
                scores.append(score)

        scores = list(set(scores))
        scores.sort(reverse=True)

        message = ''

        self.logger.debug('Adding highest scoring users to message')

        message += self._generate_message_from_list(highest)
        message += 'are ' if len(highest) != 1 else 'is '
        message += f'in the lead with {scores[0]} points. '

        if middle:
            message += self._generate_message_from_list(middle)
            message += 'are ' if len(middle) != 1 else 'is '
            message += f'in second place with {scores[1]}. '

        if lowest:
            message += self._generate_message_from_list(lowest)
            message += 'are ' if len(lowest) != 1 else 'is '
            message += f'in third place with {scores[2]}.'

        await ctx.channel.send(message)

    @commands.command(aliases='category')
    async def hint(self, ctx: commands.Context) -> None:
        """Outputs the current game's category."""

        self.logger.info('Hint was requested, attempting to send a hint')

        if not self.game.running:
            await ctx.channel.send(
                'The round has ended, a new wordlist must be set.')
            return

        category = self.game.category

        message = f'The current category is {category}'

        await ctx.channel.send(message)

    @commands.command(aliases=['wordsremaining', 'remaining',
                               'remaining_words', 'words'])
    async def words_remaining(self, ctx: commands.Context) -> None:
        """Outputs the number of words remaining."""

        self.logger.info('Remaining word count requested')

        count = self.databasemanager.get_remaining_word_count()

        message = f'There are {count} words remaining.'

        await ctx.channel.send(message)

    @commands.command(aliases=['migrateuser', 'migrate'])
    async def migrate_user(self, ctx: commands.Context) -> None:
        """Attempts to migrate the stats from one username to another."""

        self.logger.info('Checking user permissions for !migrate_user')

        user = ctx.author

        if not check_permissions(user, Permissions.BROADCASTER):
            self.logger.info(
                'User does not have permissions to run this command')

            return

        try:
            old_username, new_username, _ = parse_params(ctx.message.content, 2)
        except NotEnoughParamsException:
            self.logger.info('Did not get the new username')

            await ctx.send('!migrate_user requires two usernames, the old one '
                           'and the current one.')
            return
        try:
            self.databasemanager.migrate_user(old_username, new_username)
        except UserNotFoundException:
            self.logger.info('User was not found')

            await ctx.send(f'No user found by the name of {old_username}.')
            return

        await ctx.send(f'{old_username} has been migrated to {new_username}.')

    @commands.command(aliases=['endround'])
    async def end_round(self, ctx: commands.Context) -> None:
        """Attempts to manually end the current game round.

        Permissions:
            Broadcaster
        """

        self.logger.info('Checking user permissions for !end_round')

        user = ctx.author

        if not check_permissions(user, Permissions.BROADCASTER):
            self.logger.info(
                'User does not have permissions to run this command')

            return

        self.logger.info('Broadcaster requested the round to end')

        await self._end_round(ctx.channel)

    @commands.command(aliases=['addtokens'])
    async def add_tokens(self, ctx: commands.Context) -> None:
        """Attempts to add a specified number of tokens to a user.

        Permissions:
            Broadcaster
        """

        self.logger.info('Check user permissions for !add_tokens')

        user = ctx.author

        if not check_permissions(user, Permissions.BROADCASTER):
            self.logger.info(
                'User does not have permissions to run this command')

            return

        try:
            username, token_param, _ = parse_params(ctx.message.content, 2)
            username = parse_username(username)
            num_tokens = int(token_param)
        except NotEnoughParamsException:
            self.logger.info('Not enough params')

            await ctx.send('!add_tokens requires a username and a number of '
                           'tokens')
            return
        except ValueError:
            self.logger.info('Param 2 was not a number')

            await ctx.send('!add_tokens [username] [amount] amount must be a '
                           'number.')
            return

        self.logger.info('Broadcaster is adding tokens to user')

        try:
            self.logger.info(f'Broadcaster requested to add {num_tokens} to '
                             f'{username}')

            self.databasemanager.add_tokens(username, num_tokens)
        except UserNotFoundException:
            self.logger.info(f'User {username} was not found in database')

            await ctx.send(f'{username} was not found.')
            return

        self.logger.info(f'Successfully added {num_tokens} to {username}')

        await ctx.send(f'Successfully added {num_tokens} to {username}.')

    @commands.command(aliases=['removetokens'])
    async def remove_tokens(self, ctx: commands.Context) -> None:
        """Attempts to remove a specified number of tokens from a user.

        Permissions:
            Broadcaster
        """

        self.logger.info('Check user permissions for !remove_tokens')

        user = ctx.author

        if not check_permissions(user, Permissions.BROADCASTER):
            self.logger.info(
                'User does not have permissions to run this command')

            return

        try:
            username, token_param, _ = parse_params(ctx.message.content, 2)
            username = parse_username(username)
            num_tokens = int(token_param)
        except (NotEnoughParamsException, ValueError):
            self.logger.info('Not enough params')

            await ctx.send('!remove_tokens requires a username and a number of '
                           'tokens')
            return

        self.logger.info('Broadcaster is adding tokens to user')

        try:
            self.logger.info(f'Broadcaster requested to remove {num_tokens} '
                             f'from {username}')

            self.databasemanager.remove_tokens(username, num_tokens)
        except UserNotFoundException:
            self.logger.info(f'User {username} was not found in database')

            await ctx.send(f'{username} was not found.')
            return

        self.logger.info(f'Successfully removed {num_tokens} from {username}')

        await ctx.send(f'Successfully removed {num_tokens} from {username}.')

    @commands.command()
    async def help(self, ctx: commands.Context) -> None:
        """Outputs a link to the bot's command and usage documentation."""

        self.logger.info('Printing the help message')

        ctx.send('For help, see the bastisawesome/guessinggame_ttv wiki on '
                 'GitHub.')

    @commands.command(aliases=['redeemhelp', 'helpredeem', 'help_redeem'])
    async def redeem_help(self, ctx: commands.Context) -> None:
        """Outputs instructions to see redeem information."""

        self.logger.info('User has requests redeems help')

        await ctx.send('For information about what redeems are available, '
                       'check the streamer information below.')

    @commands.command()
    async def redeem(self, ctx: commands.Context) -> None:
        """Attempts to execute a redemption."""

        self.logger.info('User has requested to redeem')

        username = ctx.author.display_name

        try:
            redeem_name, _ = parse_params(ctx.message.content, 1)
        except NotEnoughParamsException:
            self.logger.info(f'{username} did not supply a redeem name')

            await ctx.send('!redeem requires the name of a redeem.')
            return

        try:
            redeem_cost = self.databasemanager.get_redeem_cost(redeem_name)
        except RedeemNotFoundException:
            self.logger.info(f'Redeem {redeem_name} was not found')

            await ctx.send(f'{redeem_name} is invalid, for help please use '
                           '!redeem_help.')
            return

        user_tokens = self.databasemanager.get_tokens(username)

        if user_tokens < redeem_cost:
            self.logger.info(f'{username} does not have enough tokens')

            await ctx.send(f'{redeem_name} costs {redeem_cost} tokens. You do '
                           f'not have enough tokens ({user_tokens}).')
            return

        remaining_tokens = user_tokens - redeem_cost

        self.databasemanager.remove_tokens(username, redeem_cost)

        await ctx.send(f'REDEEM {redeem_name.upper()}')
        await ctx.send(f'{username} has {remaining_tokens} tokens left.')
