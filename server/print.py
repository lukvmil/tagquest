import io
import textwrap
from typing import Annotated
from urllib.parse import quote

import segno
from PIL import Image, ImageFile
from fastapi import APIRouter, Cookie, HTTPException, Query, Request, Response
from fastapi.responses import RedirectResponse, FileResponse
from sqlalchemy import select
from escpos.printer import Dummy

from .auth import RequireLogin
from .config import settings
from .db import DatabaseSession
from .orm import Tag


# paper width in dots and font A columns for each printer
PRINTER_WIDTHS = {
    "local": (576, 48),
    "remote": (512, 42),
}

RECEIPT_REDIRECT_URI =f"https://{settings.host}/print"
RECEIPT_AUTH_URI = f"https://receipt.recurse.com/login?redirect_uri={quote(RECEIPT_REDIRECT_URI, safe='')}"

print_router = APIRouter()

@print_router.get("/print", dependencies=[RequireLogin])
def get_print(receipt_csrf: Annotated[str | None, Cookie()] = None):
    if receipt_csrf is None:
        return RedirectResponse(RECEIPT_AUTH_URI, status_code=303)
    
    return FileResponse("static/print.html")

def generate_qrcode(content: str) -> ImageFile:
    buf = io.BytesIO()
    segno.make_qr(
        content=content,
        mode="alphanumeric",
        error="M"
    ).save(
        out=buf,
        kind="png",
        scale=10
    )
    buf.seek(0)
    img = Image.open(buf)
    img.load()
    return img

def generate_bytes(tag: Tag) -> bytes:
    width_pixels, width_columns = PRINTER_WIDTHS[settings.print_mode]

    p = Dummy(profile="RP326")
    p.profile.profile_data["media"]["width"]["pixels"] = width_pixels
    # 8 dots per mm
    p.profile.profile_data["media"]["width"]["mm"] = width_pixels // 8
    
    tag_key_url = f"HTTPS://{settings.host.upper()}/K/{tag.key}"
    qr_img = generate_qrcode(tag_key_url)
    
    p.hw("INIT")
    p.set(double_height=True, double_width=True)
    # printer.textln("RC F2 '26 Demo-Palooza!")
    p.textln("TagQuest v0.6")
    
    p.set_with_default(bold=True)
    p.ln()
    p.text(f"Created by: ")
    p.set_with_default()
    p.textln(tag.user.name)
    
    p.set_with_default()
    p.set(align="center")
    p.image(qr_img)
    p.ln()
    
    # wrap as if the label were part of the text, then strip the placeholder
    # so only the first line is shortened
    quest_label = "Quest: "
    quest_text = textwrap.fill(
        tag.quest,
        width=width_columns,
        initial_indent=" " * len(quest_label)
    )
    quest_text = quest_text[len(quest_label):]

    p.set_with_default(bold=True)
    p.text(quest_label)
    p.set_with_default()
    p.text(quest_text)
    p.ln(2)
    # printer.textln("Show this tag to the person at the demo station so they can add an entry to your quest!")
    
    entry_modes = []
    if tag.txt_mode: entry_modes.append("text")
    if tag.img_mode: entry_modes.append("image")
    
    p.set_with_default(bold=True)
    p.text("Entry mode(s): ")
    p.set_with_default()
    p.textln(",".join(entry_modes) if entry_modes else "none")
    p.cut()
    return p.output

@print_router.get("/receipt")
def get_receipt(
    request: Request,
    db: DatabaseSession,
    tag_key: str | None = Query(None)
):
    # local print server passes the key directly, the browser uses the session
    if tag_key is None:
        tag_key = request.session.pop("print_tag_key", None)
    if tag_key is None:
        raise HTTPException(status_code=404, detail="Nothing to print")

    tag = db.scalars(
        select(Tag).where(Tag.key == tag_key)
    ).first()

    if not tag:
        raise HTTPException(status_code=404, detail="Invalid tag key")

    receipt_bytes = generate_bytes(tag)
    # lets the print page redirect to the tag once it's printed
    return Response(
        receipt_bytes,
        media_type="application/octet-stream",
        headers={"X-Tag-Id": str(tag.id)}
    )