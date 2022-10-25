from guessinggame_ttv.bot import (
    parse_params, NotEnoughParamsException, parse_restream_username)

import pytest


def test_parse_params_two_params() -> None:
    msg = 'param1 param2 the rest of the message'

    params = parse_params(msg, 2)

    assert len(params) == 3
    assert params[0] == 'param1'
    assert params[1] == 'param2'
    assert params[2] == 'the rest of the message'


def test_parse_params_four_params() -> None:
    msg = 'param1 param2 param3 param4 the rest of the message'

    params = parse_params(msg, 4)

    assert len(params) == 5
    assert params[0] == 'param1'
    assert params[1] == 'param2'
    assert params[2] == 'param3'
    assert params[3] == 'param4'
    assert params[4] == 'the rest of the message'


def test_parse_params_zero() -> None:
    msg = 'no parsing here'

    params = parse_params(msg, 0)

    assert len(params) == 1
    assert params[0] == 'no parsing here'


def test_parse_params_none() -> None:
    msg = 'not enough params'

    with pytest.raises(NotEnoughParamsException):
        parse_params(msg, 10)


@pytest.mark.parametrize('message,expected',
                         [['[YouTube: Test Username] Message', 'Test_Username'],
                          ['[YouTube: Username] Message', 'Username'],
                          ['[YouTube: Longer Username With Many Spaces]',
                          'Longer_Username_With_Many_Spaces']])
def test_parse_restream_username(message: str, expected: str) -> None:
    username = parse_restream_username(message)

    assert username == expected
