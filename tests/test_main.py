from guessinggame_ttv.main import (
    read_settings, configure_logging, InvalidConfigFile,
    ConfigNotExistsException)

import pytest
import pathlib
import logging


@pytest.fixture()
def config_file(tmp_path: pathlib.Path) -> pathlib.Path:
    out_path = tmp_path.joinpath(tmp_path, 'settings.conf')

    with open(out_path, 'w') as tmp_conf:
        tmp_conf.write('''[configuration]
channel = test_channel
token = bot_super_secret_token
client_secret = bot_super_secret_client_secret
prefix = !
''')

    return out_path


def test_read_settings(config_file: str) -> None:
    settings = read_settings(config_file)

    assert settings.channel == 'test_channel'
    assert settings.token == 'bot_super_secret_token'
    assert settings.client_secret == 'bot_super_secret_client_secret'
    assert settings.prefix == '!'


def test_read_settings_missing(tmp_path: pathlib.Path) -> None:
    settings_path = tmp_path.joinpath(tmp_path, 'settings.conf')

    with pytest.raises(ConfigNotExistsException):
        read_settings(settings_path)
