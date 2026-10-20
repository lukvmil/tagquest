from datetime import datetime, timezone
from enum import Enum

from sqlalchemy import DateTime, ForeignKey
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship

import server.utils as utils

class Base(DeclarativeBase):
    pass

class TagVisibility(Enum):
    PUBLIC = "public"
    UNLISTED = "unlisted"
    PRIVATE = "private"
    
class TagStatus(Enum):
    INACTIVE = "inactive"
    ACTIVE = "active"
    ARCHIVED = "archived"

class Tag(Base):
    __tablename__ = "tag"
    id: Mapped[str] = mapped_column(
        primary_key=True, default=utils.make_id)
    key: Mapped[str]

    visibility: Mapped[TagVisibility] = mapped_column(default=TagVisibility.PRIVATE)
    status: Mapped[TagStatus] = mapped_column(default=TagStatus.INACTIVE)

    activated_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    quest: Mapped[str | None]
    
    txt_mode: Mapped[bool] = mapped_column(default=False)
    geo_mode: Mapped[bool] = mapped_column(default=False)
    img_mode: Mapped[bool] = mapped_column(default=False)
    
    user_id: Mapped[int | None] = mapped_column(ForeignKey("user.id"), index=True)
    user: Mapped["User | None"] = relationship(back_populates="tags")
    
    entries: Mapped[list["Entry"]] = relationship(
        back_populates="tag", order_by="Entry.created_at")
    
    def __init__(self):
        self.id = utils.make_id()
        self.key = utils.make_key()
    
    def activate(
        self, quest: str, 
        user: "User", 
        visibility: TagVisibility,
        txt_mode: bool = False,
        img_mode: bool = False,
        geo_mode: bool = False
    ):
        self.user = user
        self.status = TagStatus.ACTIVE
        self.activated_at = datetime.now(timezone.utc)
        self.quest = quest
        self.visibility = visibility
        
        self.txt_mode = txt_mode
        self.img_mode = img_mode
        self.geo_mode = geo_mode

    def validate_entry(self, text: str | None, has_image: bool) -> str | None:
        """Returns an error message if an entry doesn't satisfy this tag's modes"""
        if self.status != TagStatus.ACTIVE:
            return "This tag isn't active"
        if self.txt_mode and not text:
            return "Text is required"
        if self.img_mode and not has_image:
            return "A photo is required"
        # TODO: geo_mode
        return None

class Entry(Base):
    __tablename__ = "entry"
    id: Mapped[int] = mapped_column(primary_key=True)
    text: Mapped[str | None]
    image_path: Mapped[str | None]
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True))
    
    user_id: Mapped[int] = mapped_column(ForeignKey("user.id"), index=True)
    user: Mapped["User"] = relationship(back_populates="entries")
    
    tag_id: Mapped[str] = mapped_column(ForeignKey("tag.id"), index=True)
    tag: Mapped["Tag"] = relationship(back_populates="entries")
    
    def __init__(
        self,
        tag: Tag,
        user: "User",
        text: str | None = None,
        image_path: str | None = None
    ):
        self.created_at = datetime.now(timezone.utc)
        self.tag = tag
        self.user = user
        self.text = text
        self.image_path = image_path

class User(Base):
    __tablename__ = "user"
    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str | None]
    
    entries: Mapped[list["Entry"]] = relationship(
        back_populates="user", order_by="Entry.created_at")
    tags: Mapped[list["Tag"]] = relationship(
        back_populates="user", order_by="Tag.activated_at")