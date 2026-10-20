from fastapi import APIRouter, Request
from sqlalchemy import or_, and_, select

from .common import GetUser, templates
from .db import DatabaseSession
from .orm import Entry, Tag, TagVisibility, User


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
        select(Tag).where(Tag.visibility == TagVisibility.PUBLIC)
    ).all()
    
    return templates.TemplateResponse(
        request=request, name="home.html", context={
            "current_user": c_user,
            "public_tags": public_tags,
            "your_tags": your_tags
        }
    )

@views_router.get("/leaderboard")
def get_leaderboard(request: Request, db: DatabaseSession, c_user: GetUser):
    print("tags:", len(c_user.tags))
    print("entries:", len(c_user.entries))
    
    users = db.scalars(select(User)).all()
    leaderboard_data = []
    for u in users:
        downstream_entries = db.scalars(
            select(Entry)
            .join(Tag, Tag.id == Entry.tag_id)
            .join(User, User.id == Tag.user_id)
            .where(and_(
                User.id == u.id,
                Entry.user_id != u.id
                )
            )
        ).all()
        
        score = 3 * len(u.tags) + 2 * len(u.entries) + len(downstream_entries)
        
        leaderboard_data.append({
            "name": u.name,
            "score": score
        })
    
    leaderboard_data.sort(
        key=lambda e: e["score"],
        reverse=True)
    
    return templates.TemplateResponse(
        request=request, name="leaderboard.html", context={
            "leaderboard_data": leaderboard_data
        }
    )