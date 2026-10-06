import io
from typing import Annotated

import segno
import uvicorn
from fastapi import APIRouter, Cookie, Depends, FastAPI, Form, HTTPException, Request
from fastapi.responses import FileResponse, HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session

from server.orm import Base, Entry, Tag


app = FastAPI()
api = APIRouter(prefix="/api")
app.include_router(api)

templates = Jinja2Templates(directory="templates")

# "postgresql+psycopg://postgres:hello-world@localhost:5432"

engine = create_engine(
    url="sqlite+pysqlite:///tagquest.db", 
    echo=True)

# Base.metadata.drop_all(engine)
Base.metadata.create_all(engine)

HOST = "127.0.0.1:8000"


def get_session():
    with Session(engine) as session:
        yield session
        
SessionDep = Annotated[Session, Depends(get_session)]


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
    
    buf = io.BytesIO()
    segno.make_qr(
        content=f"HTTP://{HOST}/K/{tag.key}",
        mode="alphanumeric",
        error="M"
    ).save(
        out=buf,
        kind="png",
        scale=10
    )
    
    # return Response(
    #     content=buf.getvalue(),
    #     media_type="image/png"
    # )
    
    return {
        "id": tag.id,
        "key": tag.key,
        "url": f"http://{HOST}/K/{tag.key}".upper()
    }

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