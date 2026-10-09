import io
import os
from typing import Annotated
from urllib.parse import quote

import segno
import uvicorn
from fastapi import APIRouter, Cookie, Depends, FastAPI, Form, HTTPException, Request, Response
from fastapi.responses import FileResponse, HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy import create_engine, or_, select
from sqlalchemy.orm import Session
from starlette.middleware.sessions import SessionMiddleware
from authlib.integrations.starlette_client import OAuth, OAuthError
from dotenv import load_dotenv

from server.orm import Base, Entry, Tag, User

load_dotenv()
SESSION_SECRET = os.getenv("SESSION_SECRET")
RC_CLIENT_ID = os.getenv("RC_CLIENT_ID")
RC_CLIENT_SECRET = os.getenv("RC_CLIENT_SECRET")

app = FastAPI()
api = APIRouter(prefix="/api")
app.include_router(api)
app.add_middleware(SessionMiddleware, secret_key=SESSION_SECRET)

oauth = OAuth()
oauth.register(
    name="recurse",
    client_id=RC_CLIENT_ID,
    client_secret=RC_CLIENT_SECRET,
    authorize_url="https://www.recurse.com/oauth/authorize",
    access_token_url="https://www.recurse.com/oauth/token",
    api_base_url="https://www.recurse.com/api/v1/"
)

templates = Jinja2Templates(directory="templates")

# "postgresql+psycopg://postgres:hello-world@localhost:5432"

engine = create_engine(
    url="sqlite+pysqlite:///tagquest.db", 
    echo=True)

# Base.metadata.drop_all(engine)
Base.metadata.create_all(engine)

HOST = "tagquest-dev.recurse.com"
RECEIPT_REDIRECT_URI = f"https://{HOST}/print"
RECEIPT_AUTH_URI = f"https://receipt.recurse.com/login?redirect_uri={quote(RECEIPT_REDIRECT_URI, safe='')}"

# HOST = "127.0.0.1:8000"

def get_session():
    with Session(engine) as session:
        yield session

DatabaseSession = Annotated[Session, Depends(get_session)]


def current_user(request: Request, db: DatabaseSession):
    user_id = request.session.get("user_id")
    user = db.get(User, user_id) if user_id else None
    return user

CurrentUser = Annotated[User, Depends(current_user)]

@app.get("/")
def get_home(request: Request, db: DatabaseSession, c_user: CurrentUser):
    your_tags = db.scalars(
        select(Tag).where(or_(
            Tag.user == c_user,
            Tag.entries.any(Entry.user == c_user),
        ))
    ).all()
    public_tags = db.scalars(
        select(Tag).where(Tag.public==True)
    ).all()
    
    return templates.TemplateResponse(
        request=request, name="home.html", context={
            "current_user": c_user,
            "public_tags": public_tags,
            "your_tags": your_tags,
            "RECEIPT_AUTH_URI": RECEIPT_AUTH_URI
        }
    )
    
@app.get("/me")
def get_me(user: CurrentUser):
    return {"name": user.name}

@app.get("/login")
async def login(request: Request):
    redirect_uri = f"https://{HOST}/auth/callback"
    return await oauth.recurse.authorize_redirect(request, redirect_uri)

@app.get("/logout")
def logout(request: Request):
    request.session.clear()
    return RedirectResponse("/", status_code=302)

@app.get("/auth/callback")
async def auth_callback(request: Request, db: DatabaseSession):
    token = await oauth.recurse.authorize_access_token(request)
    print(token)
    
    resp = await oauth.recurse.get("profiles/me", token=token)
    resp.raise_for_status()
    user_data = resp.json()
    user_id = user_data["id"]
    user_name = user_data["name"]
    
    user = db.scalar(select(User).where(User.id == user_id))
    new = False
    if user is None:
        user = User(id=user_id)
        db.add(user)
        new = True
    
    user.name = user_name
    db.commit()

    request.session["user_id"] = user_id
    
    return templates.TemplateResponse(
        request=request, name="login_success.html", context={"user": user}
    )

@app.get("/auth")
def get_auth():
    return FileResponse("static/auth.html")

@app.get("/print")
def get_print(request: Request, db: DatabaseSession):
    user_id = request.session.get("user_id")
    user = db.get(User, user_id) if user_id else None
    if user is None:
        return RedirectResponse("/login", status_code=302)
    
    return FileResponse("static/print.html")

@app.get("/K/{tag_key}")
def resolve_key(tag_key: str, db: DatabaseSession, request: Request):
    tag = db.scalars(
        select(Tag).where(Tag.key == tag_key)
    ).first()
    
    if not tag:
        return HTTPException(status_code=404, detail="Invalid tag key")
    
    user_id = request.session.get("user_id")
    user = db.get(User, user_id) if user_id else None
    if user is None:
        return RedirectResponse("/login", status_code=302)
    
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


@app.get("/new-tag")
def new_tag(db: DatabaseSession):
    tag = Tag()
    db.add(tag)
    db.commit()
    
    return {
        "id": tag.id,
        "key": tag.key,
        "url": f"http://{HOST}/K/{tag.key}".upper()
    }
    
@app.get("/k/{tag_key}/qrcode")
def get_tag_qr_code(tag_key: str):
    buf = io.BytesIO()
    url = f"https://{HOST.upper()}/K/{tag_key}".upper()
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

@app.get("/t/{tag_id}/activate")
def get_tag_activate():
    return FileResponse("static/activate_tag.html")

@app.post("/t/{tag_id}/activate")
def post_tag_activate(
    db: DatabaseSession,
    tag_id: str, 
    prompt: Annotated[str, Form()],
    visibility: Annotated[str, Form()],
    user: CurrentUser,
    tag_key: Annotated[str | None, Cookie()] = None,
):
    print("got key:", tag_key)
    tag: Tag = db.get(Tag, tag_id)
    tag.activate(
        quest=prompt,
        user=user,
        public=(visibility=="public")
    )
    db.commit()
    
    return RedirectResponse(f"/t/{tag_id}", status_code=303)


@app.get("/t/{tag_id}", response_class=HTMLResponse)
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

@app.post("/t/{tag_id}/entry")
def post_entry(
    tag_id: str,
    db: DatabaseSession,
    text: Annotated[str, Form()],
    user: CurrentUser
):
    tag: Tag = db.get(Tag, tag_id)
    entry = Entry(
        tag=tag,
        text=text,
        user=user
    )
    db.add(entry)
    db.commit()
    
    return RedirectResponse(f"/t/{tag_id}", status_code=303)


@app.get("/tags", response_class=HTMLResponse)
def get_tags(request: Request, db: DatabaseSession):
    tags = db.scalars(select(Tag)).all()
    return templates.TemplateResponse(
        request=request, name="tags.html", context={"tags": tags}
    )


if __name__ == "__main__":
    uvicorn.run(
        "server.app:app",
        reload=True,
        host="0.0.0.0",
        port=80
    )