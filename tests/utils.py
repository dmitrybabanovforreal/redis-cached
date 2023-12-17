import random, string


def random_string() -> str:
    return ''.join(random.choices(string.ascii_lowercase + '1234567890', k=16))
