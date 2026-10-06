import secrets

import nanoid


ALPHANUM = "0123456789ABCDEFGHJIKLMNOPQRSTUVWXYZ"
CROCKFORD32 = "0123456789abcdefghjkmnpqrstvwxyz"

def rand_str(alphabet: str, length: int):
    return "".join(secrets.choice(alphabet) for _ in range(length))

def make_key(n: int = 25):
    return rand_str(ALPHANUM, 25)

def make_id():
    return rand_str(CROCKFORD32, 10)
