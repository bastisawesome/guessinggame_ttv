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

# Getting Started

## Easy Install

1. [Download](https://github.com/bastisawesome/guessinggame_ttv/releases/latest)
the latest build of GuessingGame_TTV. If working in a terminal environment, use
your favourite tool for downloading from the URL above (which will grab the
latest build of GuessingGame_TTV).

Examples (Linux):

- `curl`
- `wget`

2. Extract the archive using your favourite tool.
3. [Configure](#configuration) the bot then [run](#running) the executable in
your preferred way.


## Source-Based/Developer Install

Installing GGTV from source is almost the same on all major platforms (including
BSD). With the inclusion of automated builds, it is no longer recommended to
install from source. This option should be taken _only_ if you want to beta test
or contribute.

### Dependencies

- Python 3.10+
- Pipenv
- Git (optional)

GuessingGame_TTV uses features from Python 3.10, versions below this will not
run.

#### Windows/MacOS

- Download the latest version of Python from [python.org](https://www.python.org/)
- Download Git from [git-scm](https://git-scm.com/)

#### Linux/MacOS Homebrew

Install Python and Git from your package manager.

### Setting Up The Environment

These steps are the same on all platforms, though the commands may vary slightly.

1. Use Git to clone GuessingGame_TTV, or use the download button on GitHub.

```bash
$ git clone https://github.com/bastisawesome/guessinggame_ttv.git
```

2. Install Pipenv with Pip or from your package manager (Linux/MacOS). Be sure
to update your PATH variable as described by Pip's output.

Linux/MacOS (pip3):

```bash
$ pip3 install --user pipenv
```

Windows:

```ps
> pip install --user pipenv
```

3. Install the runtime dependencies, syncing with the lock file. If you install
dependencies using `pip install`, there may be updates that break the bot. If
this happens, you will have to re-clone the repo.

```bash
$ pipenv sync --dev
```

### Execution

GuessingGame_TTV can be run in one of two ways:

1. Navigating to the location of the GuessingGame_TTV source directory,
activating Pipenv's shell, then running Python

```bash
$ cd ~/guessinggame_ttv
$ pipenv shell
$ python -m guessinggame_ttv
```

2. Or running directly with Pipenv

```bash
$ pipenv run guessinggame_ttv/src/guessinggame_ttv/main.py
```

### Building Executable

You can choose to build your own executable to use instead of running directly
from source in one of two ways:

1. From Pipenv Shell:

    1. Activate the shell

    ```bash
    $ pipenv shell
    ```

    2. Execute the build script

    ```bash
    $ python tools/build_release.py
    ```

    3. Copy the archive from `dist/` to a new location and extract it. See
    [above](#easy-install) for using the generated executable.

2. From external shell

    1. Execute the build script through Pipenv

    ```bash
    $ pipenv run build-release
    ```

    2. Copy the archive from `dist/` to a new location and extract it. See
    [above](#easy-install) for using the generated executable.

# Configuration

An example configuration file is provided in the `templates/` directory of the
source code. Copy this file into `config/` and fill in the values, following
the comments in the template.

## Generating Client Information

Twitch OAuth2 requires a few extra steps before you can use the bot. Twitch
requires you to create a separate account for the bot and connect that account
to your stream account using the developer tools.

1. Navigate to Twitch's [developer page](https://dev.twitch.tv/console)
2. Log in with the bot's account
3. Go to Applications and register a new application. For the URL, currently,
there is no support for automatically regenerating the token, so just fill in
a valid URL (for example `http://localhost`). The category should be "chat bot".
4. Copy the generated client secret into bot.conf.
5. Follow the steps for "Getting an Access Token" from [the Twitch
documentation](https://dev.twitch.tv/docs/irc/authenticate-bot), using the CLI
tools to generate a valid token with the bot's account.
6. Fill in the generated token for the Bot's access token.

# Running

Currently, the only supported method of running the bot is through the terminal.
There are plans in the future to include templates for Linux that allow you to
run the bot through `Systemd` and `Supervisorctl`. Windows and MacOS users may
need to wait and see if we are able to support similar methods for their
platforms.

The general usage of GuessingGame_TTV is the same on all major platforms, but
we describe Windows and Linux/MacOS separately primarily due to the executable
being named differently.

## Terminal

Linux/MacOS:

1. Open a terminal and navigate to the install location for GuessingGame_TTV
2. Run the bot's executable:

```bash
$ ./guessinggame_ttv
```

For more usage instructions, run:

```bash
$ ./guessinggame_ttv --help
```

Windows:

1. Open Powershell or CMD and navigate to the install location for
GuessingGame_TTV.
2. Run the bot's executable:

```ps
> .\guessinggame_ttv.exe
```

For more usage instructions, run:

```ps
> .\guessinggame_ttv.exe --help
```

# CLI

WARNING:

Make sure the bot is not running before you enter interactive mode. Any changes
made while the bot is running may be overwritten later.

The CLI, accessed by running the bot in interactive mode (`--interactive`
argument), is the primary method of configuring the bot. Future plans do
include a more user-friendly web interface.

The CLI allows you to configure the wordlist and redeems using simple menus.

# Wordlist File

The wordlist file format is one of the more complex features of
GuessingGame_TTV.
The format is based on INI configuration files, but without any values. In fact,
you can fill in values for each key and they will simply be ignored.

Each section header is a category to be added, while each option key is a
particular word to add under that category. The entire file is read into the
database. The file will not be deleted after it has been read.

IMPORTANT: This will wipe the existing wordlist and the option should only be
used when there is no currently-running round, as it will not end the round.

An example wordlist file is included in the `templates/` directory.

# RestreamIO

GuessingGame_TTV has support for Restream messages. Viewers on YouTube and other
platforms can participate just the same as Twitch users.

Users on platforms that allow spaces in usernames, such as YouTube, are stored
with underscores in place of spaces. To view their scores or tokens the spaces
must be replaced with underscores. Their usernames in messages will also reflect
this.
