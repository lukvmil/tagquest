import io
import os
from typing import Annotated

import segno
import uvicorn
from fastapi import APIRouter, Cookie, Depends, FastAPI, Form, HTTPException, Request, Response
from fastapi.responses import FileResponse, HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session
from starlette.middleware.sessions import SessionMiddleware
from authlib.integrations.starlette_client import OAuth, OAuthError
from dotenv import load_dotenv

from server.orm import Base, Entry, Tag

load_dotenv()
SESSION_SECRET = os.getenv("SESSION_SECRET")
RC_AUTH_ID = os.getenv("RC_AUTH_ID")
RC_AUTH_SECRET = os.getenv("RC_AUTH_SECRET")

app = FastAPI()
api = APIRouter(prefix="/api")
app.include_router(api)
app.add_middleware(SessionMiddleware, secret_key=SESSION_SECRET)

oauth = OAuth()
oauth.register(
    name="recurse",
    client_id=os.getenv("RC_CLIENT_ID"),
    client_secret=os.getenv("RC_CLIENT_SECRET"),
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

# HOST = "tagquest.recurse.com"
HOST = "127.0.0.1:8000"

def get_session():
    with Session(engine) as session:
        yield session
        
SessionDep = Annotated[Session, Depends(get_session)]


@app.get("/")
def get_home(request: Request, session: SessionDep):
    tags = session.scalars(select(Tag)).all()
    return templates.TemplateResponse(
        request=request, name="home.html", context={"tags": tags}
    )

@app.get("/login")
async def login(request: Request):
    redirect_uri = "https://tagquest.recurse.com/auth/callback"
    return await oauth.recurse.authorize_redirect(request, redirect_uri)

@app.get("/auth/callback")
async def auth_callback(request: Request):
    token = await oauth.recurse.authorize_access_token(request)
    user = token["userinfo"]
    return dict(user)

@app.get("/auth")
def get_auth():
    return FileResponse("static/auth.html")

@app.get("/print")
def get_print():
    return FileResponse("static/print.html")

@app.get("/K/{tag_key}")
def resolve_key(tag_key: str, session: SessionDep):
    tag = session.scalars(
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


@app.get("/new-tag")
def new_tag(session: SessionDep):
    tag = Tag()
    session.add(tag)
    session.commit()
    
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
    session: SessionDep,
    tag_id: str, 
    prompt: Annotated[str, Form()],
    tag_key: Annotated[str | None, Cookie()] = None,
):
    print("got key:", tag_key)
    tag: Tag = session.get(Tag, tag_id)
    tag.activate(quest=prompt)
    session.commit()
    
    return RedirectResponse(f"/t/{tag_id}", status_code=303)


@app.get("/t/{tag_id}", response_class=HTMLResponse)
def get_tag(
    request: Request, 
    tag_id: str, 
    session: SessionDep,
    tag_key: Annotated[str | None, Cookie()] = None
):
    tag: Tag = session.get(Tag, tag_id)
    valid_key: bool = (tag_key == tag.key)
    print(f"got tag key: {tag_key}, valid: {valid_key}, expected: {tag.key}")
    
    entries = session.scalars(
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
    session: SessionDep,
    text: Annotated[str, Form()]
):
    tag: Tag = session.get(Tag, tag_id)
    entry = Entry(
        tag=tag,
        text=text
    )
    session.add(entry)
    session.commit()
    
    return RedirectResponse(f"/t/{tag_id}", status_code=303)


@app.get("/tags", response_class=HTMLResponse)
def get_tags(request: Request, session: SessionDep):
    tags = session.scalars(select(Tag)).all()
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