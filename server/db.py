from typing import Annotated

from fastapi import Depends
from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from .orm import Base


engine = create_engine(
    url="sqlite+pysqlite:///tagquest.db", 
    echo=True)

Base.metadata.create_all(engine)

def get_session():
    with Session(engine) as session:
        yield session

DatabaseSession = Annotated[Session, Depends(get_session)]
