from guessinggame_ttv.database import DatabaseManager
from guessinggame_ttv.bot import GuessingGameBot
from guessinggame_ttv. interface import Interface
from guessinggame_ttv.utils import Settings

import configupdater

import argparse
import sys
import logging
import pathlib
import configparser

from typing import Tuple


class GuessingGameTtvException(Exception):
    pass


class ConfigNotExistsException(GuessingGameTtvException):
    pass


class WordlistFileNotFoundException(GuessingGameTtvException):
    pass


class InvalidWordlistFile(GuessingGameTtvException):
    pass


class InvalidConfigFile(GuessingGameTtvException):
    pass


def read_settings(
    settings_path: pathlib.Path = pathlib.Path(
        './config/bot.conf')
) -> Settings:
    logger = logging.getLogger('guessinggame_ttv')

    dir_path = settings_path.parent if settings_path.suffix else settings_path
    file_path = settings_path.joinpath(
        'bot.conf') if not settings_path.suffix else settings_path

    if not dir_path.exists():
        logger.info('Creating settings path')

        dir_path.mkdir(parents=True)

    if not file_path.exists():
        logger.info('File does not exist, raising exception')

        raise ConfigNotExistsException()

    conf = configupdater.ConfigUpdater(
        empty_lines_in_values=False,
        allow_no_value=False
    )

    conf.read(file_path)

    try:
        options = conf.get_section('configuration')

        s = Settings(
            channel=options['channel'].value,
            token=options['token'].value,
            client_secret=options['client_secret'].value,
            prefix=options['prefix'].value,
        )
    except (KeyError, ValueError):
        raise InvalidConfigFile()

    return s


def configure_logging(
        use_stdout: bool,
        file_path: pathlib.Path | None = None,
        verbosity: int = logging.INFO) -> None:
    logger = logging.getLogger('guessinggame_ttv')
    logger.setLevel(verbosity)

    fmt = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(message)s')

    if use_stdout:
        stdout_handler = logging.StreamHandler()
        stdout_handler.setFormatter(fmt)
        logger.addHandler(stdout_handler)

    if not file_path:
        file_path = pathlib.Path('./logs')

    if not file_path.exists():
        file_path.mkdir(parents=True)

    file_handler = logging.FileHandler(
        file_path.joinpath('gussinggame_ttv.log'))
    file_handler.setFormatter(fmt)
    logger.addHandler(file_handler)


def wordlist_from_file(wordlist_path: pathlib.Path) -> None:
    logger = logging.getLogger('guessinggame_ttv')

    logger.info('Attempting to read wordlist file')

    if not wordlist_path.exists():
        raise WordlistFileNotFoundException()

    cfg_parser = configparser.ConfigParser(
        allow_no_value=True,
        empty_lines_in_values=False,
        default_section=None
    )

    cfg_parser.read(wordlist_path)

    if cfg_parser.defaults() or not cfg_parser.sections():
        raise InvalidWordlistFile()

    wordlist: dict[str, list[str]] = {}

    for section in cfg_parser.sections():
        wordlist[section] = []
        for option in cfg_parser.options(section):
            wordlist[section].append(option)

    dbman = DatabaseManager()
    dbman.set_wordlist(wordlist)
    dbman.reset_round()


def parse_args(args: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        prog='GuessingGame_TTV',
        description=('Controls a Twitch bot that plays a word guessing game.\n '
                     'License: New BSD 3-Clause'),
        epilog=('(c) 2022 Giles Johnson. For more information '
                'see https://github.com/bastisawesome/guessinggame_ttv')
    )

    parser.add_argument(
        '-v', '--verbose',
        action='count',
        help=('Sets the output verbosity in the order of: warning, info, debug'
              '\nOnly applicable when not running as daemon, overrides the '
              'log_level configuration file setting.'),
        default=0
    )

    parser.add_argument(
        '-w', '--from-wordlist',
        action='store',
        type=str,
        help=('Read a wordlist from an INI-formatted file and set the wordlist '
              'in the database. This will reset the existing wordlist.\n'
              '(see README for information)'),
        dest='wordlist_file'
    )

    parser.add_argument(
        '-d', '--daemonise',
        action='store_true',
        help=('Configure GuessingGame_TTV to run as a daemon. This is the '
              'default behaviour.')
    )

    parser.add_argument(
        '-i', '--interactive',
        action='store_true',
        help=('Run the application in interactive mode, loading the console '
              'interface.')
    )

    parser.add_argument(
        '-o', '--log-output',
        action='store',
        type=str,
        help='Choose an output directory for the log file.',
        dest='log_dir'
    )

    return parser.parse_args(args)


def validate_args(
    args: argparse.Namespace
) -> Tuple[bool, str, str]:
    """Ensures that conflicting arguments have not been used together.

    Args:
        args (argparse.Namespace): ArgParse Namespace of arguments.

    Returns:
        tuple[bool, Optional[Tuple[str, str]]]:
            The success value and, if unsuccessful, a tuple of conflicting
            arguments.
    """

    if args.interactive and args.daemonise:
        return (False, 'interactive', 'daemonise')

    if args.interactive and args.verbose:
        return (False, 'interactive', 'verbose')

    return (True, '', '')


def run(settings: Settings) -> None:
    with GuessingGameBot(settings) as bot:
        bot.run()


def convert_verbosity(verbosity: int) -> int:
    if verbosity == 0:
        return logging.ERROR
    elif verbosity == 1:
        return logging.WARNING
    elif verbosity == 2:
        return logging.INFO
    else:
        return logging.DEBUG


def main() -> None:
    args = parse_args()

    success, arg1, arg2 = validate_args(args)

    if not success:
        print(f'--{arg1} is incompatible with --{arg2}')

        sys.exit(1)

    if not pathlib.Path('./config').exists():
        pathlib.Path('./config').mkdir()

    verbosity = convert_verbosity(args.verbose)
    daemonise = args.daemonise or not args.interactive

    if args.log_dir:
        configure_logging(daemonise, args.log_dir, verbosity)
    else:
        configure_logging(daemonise, verbosity=verbosity)

    logger = logging.getLogger('guessinggame_ttv')

    if args.wordlist_file:
        try:
            wordlist_from_file(pathlib.Path(args.wordlist_file))
        except WordlistFileNotFoundException:
            logger.error(f'{args.wordlist_file} could not be found, check to '
                         'make sure it exists and permissions are set'
                         'correctly')

            sys.exit(1)
        except InvalidWordlistFile:
            logger.error(f'{args.wordlist_file} was not properly formatted, '
                         'please read the README for information on how to '
                         'format a wordlist file')

            sys.exit(1)

    if args.interactive:
        with Interface(DatabaseManager()) as interface:
            interface.run()
        sys.exit(0)

    try:
        settings = read_settings()
    except (ConfigNotExistsException, InvalidConfigFile):
        logger.error('bot.conf does not exist or is not formatted correctly, '
                     'copy from templates directory or download a template '
                     'from the GitHub repo.')

        sys.exit(1)

    run(settings)


if __name__ == '__main__':
    main()
