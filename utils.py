import secrets

import nanoid


HEX_DIGITS = "0123456789ABCDEF"

def make_id():
    return nanoid.generate()
