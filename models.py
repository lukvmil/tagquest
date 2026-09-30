from datetime import datetime

from pydantic import BaseModel


class TagOut(BaseModel):
    id: str
    # public: bool
    active: bool
    activated_at: datetime
    quest: str