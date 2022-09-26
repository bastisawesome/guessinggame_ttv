from guessinggame_ttv.database import DatabaseManager

import logging
import pytest

logging.disable()


@pytest.fixture
def dbmanager() -> DatabaseManager:
    return DatabaseManager(_use_test=True)
