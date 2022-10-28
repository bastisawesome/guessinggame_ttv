# GuessingGame_TTV

A Twitch bot that runs a simple word-guessing game. It provides features that
allow chatters to guess words and earn points and tokens.

The game is played in rounds, where each round consists of a supplied wordlist.
When every word in the wordlist has been guessed, or upon manually ending the
round, players are awarded with tokens which can be used to call the bot's
built-in redeem system.

The redeem system is, currently, very simple in design: it verifies the user
has enough tokens, then writes a message in chat in the format of
"REDEEM redeem_name". Then the tokens are subtracted from the user who called
the command.

# What This Bot Is Not

This is not a general-purpose bot. The sole purpose of GuessingGame_TTV is,
as the name implies, to run the guessing game. There are no plans to expand
the features to allow for moderation or more advanced configurations, unrelated
to the guessing game.

# Running

GuessingGame_TTV works the same on all major operating systems.

## Dependencies

- Python 3.10+
- Pipenv
- Git (optional)

GuessingGame_TTV uses features from Python 3.10, versions below this will not
run.

### Windows/MacOS

- Download the latest version of Python from [python.org](https://www.python.org/)
- Download Git from [git-scm](https://git-scm.com/)

### Linux/Mac OS Homebrew

Install Python and Git from your package manager.

## Setting Up The Environment

These steps are the same on all platforms, though the commands may vary slightly.

1. Use Git to clone GuessingGame_TTV, or use the download button on GitHub.

```bash
$ git clone https://github.com/bastisawesome/guessinggame_ttv.git
```

2. Install Pipenv with Pip or from your package manager.

```bash
$ pip3 install --user pipenv
```

3. Install the runtime dependencies.

```bash
$ pipenv install
```

## Execution

GuessingGame_TTV can be run in one of two ways:

1. Navigating to the location of the GuessingGame_TTV source directory,
activating Pipenv's shell, then running Python

```bash
$ cd ~/guessinggame_ttv
$ pipenv shell
$ python src/guessinggame_ttv/main.py
```

2. Or running directly with Pipenv

```bash
$ pipenv run guessinggame_ttv/src/guessinggame_ttv/main.py
```

There are plans to add a deployment system and make it easier to run the bot
(see #6 and #10)

# Configuration

An example configuration file is provided in the `templates/` directory of the
source code. Copy this file into `config/` and fill in the values, following
the comments in the template.

## Generating Client Information

Twitch OAuth2 requires a few extra steps before you can use the bot. Twitch
requires you to create a separate account for the bot and connect that account
to your stream account using the developer tools.

1. Navigate to Twitch's [developer page](https://dev.twitch.tv/console)
2. Log in with your account
3. Go to Applications and register a new application. For the URL, currently,
there is no support for automatically regenerating the token, so just fill in
a valid URL (for example `http://localhost`). The category should be "chat bot".
4. Copy the generated client secret into bot.conf.
5. Follow the steps for "Getting an Access Token" from [the Twitch
documentation](https://dev.twitch.tv/docs/irc/authenticate-bot), using the CLI
tools to generate a valid token with the bot's account.
6. Fill in the generated token for the Bot's access token.

# CLI Interface

The CLI interface, accessed by running the bot in interactive mode (`-i`
argument), is the primary method of configuring the bot. Future plans do
include a more user-friendly web interface.

The CLI interface allows you to configure the wordlist and redeems using simple
menus.

# Wordlist File

The wordlist file format is one of the more complex features of GuessingGame_TTV.
The format is based on INI configuration files, but without any values. In
fact, you can fill in values for each key and they will simply be ignored.

Each section header is a category to be added, while each option key is a
particular word to add under that category. The entire file is read into the
database. The file will not be deleted after it has been read.

IMPORTANT: This will wipe the existing wordlist and the option should only be
used when there is no currently-running round, as it will not end the round.

An example wordlist file is included in the `templates/` directory.

# RestreamIO

GuessingGame_TTV has support for Restream messages. Viewers on YouTube and other
platforms can participate just the same as Twitch users.

Users on platforms, such as YouTube, that allow spaces in usernames are stored
with underscores in place of spaces. To view their scores or tokens the spaces
must be replaced with underscores. Their usernames in messages will also reflect
this.
