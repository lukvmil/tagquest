from authlib.integrations.starlette_client import OAuth, OAuthError
from fastapi import APIRouter, Depends, Request
from fastapi.responses import FileResponse, RedirectResponse
from sqlalchemy import select

from .config import settings
from .orm import User
from .db import DatabaseSession
from .common import templates

oauth = OAuth()
oauth.register(
    name="recurse",
    client_id=settings.rc_client_id,
    client_secret=settings.rc_client_secret.get_secret_value(),
    authorize_url="https://www.recurse.com/oauth/authorize",
    access_token_url="https://www.recurse.com/oauth/token",
    api_base_url="https://www.recurse.com/api/v1/"
)

auth_router = APIRouter()

@auth_router.get("/login")
async def login(request: Request):
    redirect_uri = f"https://{settings.host}/auth/callback"
    return await oauth.recurse.authorize_redirect(request, redirect_uri)

@auth_router.get("/logout")
def logout(request: Request):
    request.session.clear()
    return RedirectResponse("/", status_code=302)

@auth_router.get("/auth/callback")
async def auth_callback(request: Request, db: DatabaseSession):
    try:
        token = await oauth.recurse.authorize_access_token(request)
    except OAuthError:
        return FileResponse("static/login_failure.html")
    
    resp = await oauth.recurse.get("profiles/me", token=token)
    resp.raise_for_status()
    user_data = resp.json()
    user_id = user_data["id"]
    user_name = user_data["name"]
    
    user = db.scalar(select(User).where(User.id == user_id))
    if user is None:
        user = User(id=user_id)
        db.add(user)
    
    user.name = user_name
    db.commit()

    request.session["user_id"] = user_id
    
    next_url = request.session.pop("next", "/")
    
    return templates.TemplateResponse(
        request=request, name="login_success.html", context={
            "user": user,
            "redirect_uri": next_url
        }
    )


class LoginRequired(Exception):
    ...

def require_login(request: Request, db: DatabaseSession):
    user_id = request.session.get("user_id")
    user = db.get(User, user_id) if user_id else None
    
    if not user:
        url = request.url.path
        request.session["next"] = url
        raise LoginRequired()

RequireLogin = Depends(require_login)

def login_required_handler(request: Request, exc: LoginRequired):
    return RedirectResponse("/login", status_code=303)
