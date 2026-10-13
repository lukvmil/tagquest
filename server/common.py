from typing import Annotated

from fastapi import Depends, Request
from fastapi.templating import Jinja2Templates

from .db import DatabaseSession
from .orm import User


templates = Jinja2Templates(directory="templates")

def current_user(request: Request, db: DatabaseSession):
    user_id = request.session.get("user_id")
    user = db.get(User, user_id) if user_id else None
    return user

GetUser = Annotated[User, Depends(current_user)]
