from fastapi import Depends, FastAPI
from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session
from models import Base, Tag


app = FastAPI()
engine = create_engine("postgresql+psycopg://postgres:hello-world@localhost:5432", echo=True)
Base.metadata.create_all(engine)

def get_session():
    with Session(engine) as session:
        yield session

@app.post("/tag")
def create_tag(session: Session = Depends(get_session)):
    tag = Tag()
    session.add(tag)
    session.commit()
    
    return tag.id
    
@app.post("/tag/{tag_id}")
def read_tag(tag_id: str, session: Session = Depends(get_session)):
    tag = session.get(Tag, tag_id)
    tag.activate()
    session.commit()
    
@app.get("/tag/{tag_id}")
def read_tag(tag_id: str, session: Session = Depends(get_session)):
    tag = session.get(Tag, tag_id)
    return {
        "id": tag.id,
        "public": tag.public,
        "active": tag.active
    }


@app.put("/tag/{tag_id}")
def update_tag(tag_id: str, session: Session = Depends(get_session)):
    ...
    
@app.delete("/tag/{tag_id}")
def delete_tag(tag_id, session: Session = Depends(get_session)):
    ...

"""
What endpoints do I need?

- create a tag
- read a tag 
- update a tag ?
- delete a tag ?

- create an entry
- read a tag's entries

"""
