from datetime import datetime, timezone

from sqlalchemy import DateTime, ForeignKey
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship

import server.utils as utils

class Base(DeclarativeBase):
    pass

class Tag(Base):
    __tablename__ = "tag"
    id: Mapped[str] = mapped_column(
        primary_key=True, default=utils.make_id)
    key: Mapped[str]
    public: Mapped[bool] = mapped_column(default=False)
    active: Mapped[bool] = mapped_column(default=False)
    activated_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True))
    quest: Mapped[str | None]
    
    entries: Mapped[list["Entry"]] = relationship(
        back_populates="tag", order_by="Entry.created_at")
    
    def __init__(self):
        self.id = utils.make_id()
        self.key = utils.make_key()
    
    def activate(self, quest: str):
        self.active = True
        self.activated_at = datetime.now(timezone.utc)
        self.quest = quest
        
class Entry(Base):
    __tablename__ = "entry"
    id: Mapped[int] = mapped_column(primary_key=True)
    text: Mapped[str]
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True))
        
    tag_id: Mapped[str] = mapped_column(ForeignKey("tag.id"), index=True)
    tag: Mapped["Tag"] = relationship(back_populates="entries")
    
    def __init__(self, tag, text):
        self.created_at = datetime.now(timezone.utc)
        self.tag = tag
        self.text = text
    