from guessinggame_ttv.bot import (
    parse_params, NotEnoughParamsException, parse_restream_username)

import pytest


@pytest.mark.parametrize('message, num_params, params',
                         [['param1 param2 the rest of the message',
                          2, ['param1', 'param2', 'the rest of the message']],
                          ['param1 param2 param3 param4 the rest',
                          4, ['param1', 'param2', 'param3', 'param4',
                              'the rest']],
                          ['no parsing here', 0, ['!com no parsing here']]])
def test_parse_params(message: str, num_params: int,
                      params: list[str]) -> None:
    full_message = f'!com {message}'

    ret_params = parse_params(full_message, num_params)

    assert len(ret_params) == num_params+1

    for index, param in enumerate(ret_params):
        assert param == params[index]


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
