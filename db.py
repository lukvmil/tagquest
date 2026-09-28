import nanoid
from sqlalchemy import create_engine, select, text
from sqlalchemy.orm import Session
from models import Base, Tag

# postgresql+psycopg://postgres:hello-world@localhost:5432

engine = create_engine("sqlite://", echo=True)

Base.metadata.create_all(engine)

with Session(engine) as session:
    tag1 = Tag(
        id=nanoid.generate()
    )
    tag2 = Tag(
        id="beef14"
    )
    session.add_all([tag1, tag2])
    session.commit()
    
session = Session(engine)
stmt = select(Tag).where(Tag.id.in_(["beef14"]))
for user in session.scalars(stmt):
    print(user.public)