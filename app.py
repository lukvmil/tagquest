from datetime import datetime, timezone

from fastapi import Depends, FastAPI
from pydantic import BaseModel
from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session
from orm import Base, Entry, Tag

from models import TagOut


app = FastAPI()
engine = create_engine("postgresql+psycopg://postgres:hello-world@localhost:5432", echo=True)
# Base.metadata.drop_all(engine)
Base.metadata.create_all(engine)

def get_session():
    with Session(engine) as session:
        yield session

@app.post("/tag")
def create_tag(session: Session = Depends(get_session)):
    tag = Tag()
    session.add(tag)
    session.commit()
    
    return {
        "id": tag.id
    }
    
@app.post("/tag/{tag_id}")
def activate_tag(tag_id: str, session: Session = Depends(get_session)):
    tag = session.get(Tag, tag_id)
    tag.activate()
    session.commit()
    
@app.get("/tag/{tag_id}", response_model=TagOut)
def read_tag(tag_id: str, session: Session = Depends(get_session)):
    tag = session.get(Tag, tag_id)
    return tag


@app.put("/tag/{tag_id}")
def update_tag(tag_id: str, session: Session = Depends(get_session)):
    ...
    
@app.delete("/tag/{tag_id}")
def delete_tag(tag_id, session: Session = Depends(get_session)):
    ...


class EntryIn(BaseModel):
    text: str

@app.post("/tag/{tag_id}/entry")
def create_entry(tag_id: str, entry_in: EntryIn, session: Session = Depends(get_session)):
    tag = session.get(Tag, tag_id)
    entry = Entry(
        tag=tag, 
        created_at=datetime.now(timezone.utc),
        text=entry_in.text
    )
    session.add(entry)
    session.commit()

@app.get("/tag/{tag_id}/entry")
def get_entries(tag_id: str, session: Session = Depends(get_session)):
    tag = session.get(Tag, tag_id)
    return tag.entries

"""
What endpoints do I need?

- create a tag
- read a tag 
- update a tag ?
- delete a tag ?

- create an entry
- read a tag's entries

"""
