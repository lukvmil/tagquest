from typing import Annotated

from fastapi import APIRouter, Cookie, Form, HTTPException, Request
from fastapi.responses import FileResponse, HTMLResponse, RedirectResponse
from sqlalchemy import select

from .auth import RequireLogin
from .db import DatabaseSession
from .orm import Entry, Tag
from .common import templates, GetUser


tag_router = APIRouter()


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
    
    if tag.active:
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
    tag_id: str, 
    quest: Annotated[str, Form()],
    visibility: Annotated[str, Form()],
    user: GetUser,
    tag_key: Annotated[str | None, Cookie()] = None,
):
    print("got key:", tag_key)
    tag: Tag = db.get(Tag, tag_id)
    tag.activate(
        quest=quest,
        user=user,
        public=(visibility=="public")
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
            "valid_key": valid_key
        }
    )

@tag_router.post("/t/{tag_id}/entry")
def post_entry(
    tag_id: str,
    db: DatabaseSession,
    text: Annotated[str, Form()],
    user: GetUser
):
    tag: Tag = db.get(Tag, tag_id)
    entry = Entry(
        tag=tag,
        text=text,
        user=user
    )
    db.add(entry)
    db.commit()
    
    resp = RedirectResponse(f"/t/{tag_id}", status_code=303)
    resp.delete_cookie("tag_key")
    return resp