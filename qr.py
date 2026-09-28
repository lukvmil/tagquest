import segno
import secrets

alphanum = "0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZ"
hexcode = "01234567989ABCDEF"



def make_id(length: int = 8):
    return "".join(secrets.choice(alphanum) for _ in range (length))

qr = segno.make_qr(
    content=f"HTTPS://TAGQUEST.NET/T/{make_id()}",
    mode="alphanumeric",
    error="Q"
)

print(qr.designator)
print(qr.mode)

qr.save("test.png")