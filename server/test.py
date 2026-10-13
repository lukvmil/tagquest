import io

import segno
from fastapi import APIRouter, Response

from .common import GetUser
from .db import DatabaseSession
from .orm import Tag
from .config import settings


test_router = APIRouter()

@test_router.get("/new-tag")
def new_tag(db: DatabaseSession):
    tag = Tag()
    db.add(tag)
    db.commit()
    
    return {
        "id": tag.id,
        "key": tag.key,
        "url": f"http://{settings.host}/K/{tag.key}".upper()
    }

@test_router.get("/k/{tag_key}/qrcode")
def get_tag_qr_code(tag_key: str):
    buf = io.BytesIO()
    url = f"https://{settings.host.upper()}/K/{tag_key}".upper()
    segno.make_qr(
        content=url,
        mode="alphanumeric",
        error="M"
    ).save(
        out=buf,
        kind="png",
        scale=10
    )
    
    return Response(
        content=buf.getvalue(),
        media_type="image/png"
    )
    
@test_router.get("/me")
def get_me(user: GetUser):
    return {"name": user.name}
