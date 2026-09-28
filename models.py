from datetime import datetime, timezone

from sqlalchemy import DateTime
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column

import utils

class Base(DeclarativeBase):
    pass

class Tag(Base):
    __tablename__ = "tag"
    id: Mapped[str] = mapped_column(
        primary_key=True, default=utils.make_id)
    public: Mapped[bool] = mapped_column(default=False)
    active: Mapped[bool] = mapped_column(default=False)
    activated_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True))
    quest: Mapped[str | None]
    
    def activate(self):
        self.active = True
        self.activated_at = datetime.now(timezone.utc)
    
# class Entry(Base):
#     __tablename__ = "entry"
    
    