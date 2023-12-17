import random

import pytest

from tests.utils import random_string


@pytest.fixture(scope='function')
def salt() -> str:
    return random_string()


@pytest.fixture(scope='function')
def random_int() -> int:
    return random.randint(1, 1000)