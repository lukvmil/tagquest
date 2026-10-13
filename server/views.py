from fastapi import APIRouter, Request
from sqlalchemy import or_, select

from .common import GetUser, templates
from .db import DatabaseSession
from .orm import Entry, Tag


views_router = APIRouter()

@views_router.get("/")
def get_home(request: Request, db: DatabaseSession, c_user: GetUser):
    your_tags = db.scalars(
        select(Tag).where(or_(
            Tag.user == c_user,
            Tag.entries.any(Entry.user == c_user),
        ))
    ).all() if c_user else []
    public_tags = db.scalars(
        select(Tag).where(Tag.public==True)
    ).all()
    
    return templates.TemplateResponse(
        request=request, name="home.html", context={
            "current_user": c_user,
            "public_tags": public_tags,
            "your_tags": your_tags
        }
    )