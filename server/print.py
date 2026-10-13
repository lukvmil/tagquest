from typing import Annotated
from urllib.parse import quote

from fastapi import APIRouter, Cookie
from fastapi.responses import FileResponse, RedirectResponse

from .auth import RequireLogin
from .config import settings


RECEIPT_REDIRECT_URI = f"https://{settings.host}/print"
RECEIPT_AUTH_URI = f"https://receipt.recurse.com/login?redirect_uri={quote(RECEIPT_REDIRECT_URI, safe='')}"

print_router = APIRouter()

@print_router.get("/print", dependencies=[RequireLogin])
def get_print(receipt_csrf: Annotated[str | None, Cookie()] = None):
    if receipt_csrf is None:
        return RedirectResponse(RECEIPT_AUTH_URI, status_code=303)
    
    return FileResponse("static/print.html")
