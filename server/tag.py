from pathlib import Path
from typing import Annotated
from uuid import uuid4

from fastapi import APIRouter, Cookie, File, Form, HTTPException, Request, UploadFile
from fastapi.concurrency import run_in_threadpool
from fastapi.responses import FileResponse, HTMLResponse, RedirectResponse
from sqlalchemy import select

from .auth import RequireLogin
from .db import DatabaseSession
from .images import InvalidImage, process_image
from .orm import Entry, Tag, TagStatus, TagVisibility
from .common import templates, GetUser


tag_router = APIRouter()

MAX_IMAGE_BYTES = 20 * 1024 * 1024
UPLOAD_DIR = Path("uploads")
UPLOAD_DIR.mkdir(exist_ok=True)


@tag_router.get("/K/{tag_key}", dependencies=[RequireLogin])
def resolve_key(
    tag_key: str, 
    db: DatabaseSession
):
    tag = db.scalars(
        select(Tag).where(Tag.key == tag_key)
    ).first()
    
    if not tag:
        return HTTPException(status_code=404, detail="Invalid tag key")
    
    if tag.status == TagStatus.ACTIVE:
        resp = RedirectResponse(f"/t/{tag.id}", status_code=302)
    else:
        resp = RedirectResponse(f"/t/{tag.id}/activate", status_code=302)
    
    resp.set_cookie(
        key="tag_key", 
        value=tag_key,
        max_age=900,
        secure=False
    )
    return resp


@tag_router.get("/t/{tag_id}/activate")
def get_tag_activate():
    return FileResponse("static/activate_tag.html")

@tag_router.post("/t/{tag_id}/activate")
def post_tag_activate(
    db: DatabaseSession,
    user: GetUser,
    tag_id: str, 
    quest: Annotated[str, Form()],
    visibility: Annotated[TagVisibility, Form()],
    txt_mode: Annotated[bool, Form()] = False,
    img_mode: Annotated[bool, Form()] = False,
    geo_mode: Annotated[bool, Form()] = False,
    tag_key: Annotated[str | None, Cookie()] = None,
):
    print("got key:", tag_key)
    tag: Tag = db.get(Tag, tag_id)
    tag.activate(
        quest=quest,
        user=user,
        visibility=visibility,
        txt_mode=txt_mode,
        img_mode=img_mode,
        geo_mode=geo_mode
    )
    db.commit()
    
    return RedirectResponse(f"/t/{tag_id}", status_code=303)


@tag_router.get("/t/{tag_id}", response_class=HTMLResponse)
def get_tag(
    request: Request, 
    tag_id: str, 
    db: DatabaseSession,
    tag_key: Annotated[str | None, Cookie()] = None
):
    tag: Tag = db.get(Tag, tag_id)
    valid_key: bool = (tag_key == tag.key)
    print(f"got tag key: {tag_key}, valid: {valid_key}, expected: {tag.key}")
    
    entries = db.scalars(
        select(Entry).where(Entry.tag == tag)
    ).all()
    
    return templates.TemplateResponse(
        request=request, name="tag.html", context={
            "tag": tag,
            "entries": entries,
            "valid_key": valid_key,
            "entry_error": request.session.pop("entry_error", None)
        }
    )

@tag_router.post("/t/{tag_id}/entry")
async def post_entry(
    request: Request,
    tag_id: str,
    db: DatabaseSession,
    user: GetUser,
    text: Annotated[str | None, Form()] = None,
    image: Annotated[UploadFile | None, File()] = None,
    tag_key: Annotated[str | None, Cookie()] = None,
):
    tag: Tag | None = db.get(Tag, tag_id)
    if not tag:
        raise HTTPException(status_code=404, detail="Tag not found")

    def fail(error: str):
        request.session["entry_error"] = error
        return RedirectResponse(f"/t/{tag_id}", status_code=303)

    if tag_key != tag.key:
        return fail("Scan this tag's QR code to add an entry")

    # blank inputs count as missing
    if text is not None:
        text = text.strip() or None
    if image is not None and not image.filename:
        image = None

    error = tag.validate_entry(text, has_image=image is not None)
    if error:
        return fail(error)

    # inputs for modes the tag doesn't use are ignored
    if not tag.txt_mode:
        text = None

    image_name = None
    if tag.img_mode and image:
        data = await image.read(MAX_IMAGE_BYTES + 1)
        if len(data) > MAX_IMAGE_BYTES:
            return fail(f"Image is too large (max {MAX_IMAGE_BYTES // (1024 * 1024)} MB)")

        # decoding/encoding is CPU-bound, keep it off the event loop
        try:
            data = await run_in_threadpool(process_image, data)
        except InvalidImage:
            return fail("Upload must be an image")

        image_name = f"{uuid4().hex}.webp"
        (UPLOAD_DIR / image_name).write_bytes(data)

    entry = Entry(
        tag=tag,
        user=user,
        text=text,
        image_name=image_name
    )
    db.add(entry)
    db.commit()
    
    resp = RedirectResponse(f"/t/{tag_id}", status_code=303)
    resp.delete_cookie("tag_key")
    return resp