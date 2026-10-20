from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from starlette.exceptions import HTTPException
from starlette.middleware.sessions import SessionMiddleware

from .config import settings
from .auth import auth_router, LoginRequired, login_required_handler
from .error import http_error_handler
from .tag import tag_router, UPLOAD_DIR
from .views import views_router
from .print import print_router
from .test import test_router


app = FastAPI()
app.include_router(auth_router)
app.include_router(tag_router)
app.include_router(views_router)
app.include_router(print_router)
app.include_router(test_router)
app.mount("/uploads", StaticFiles(directory=UPLOAD_DIR), name="uploads")
app.add_exception_handler(LoginRequired, login_required_handler)
app.add_exception_handler(HTTPException, http_error_handler)
app.add_middleware(SessionMiddleware, secret_key=settings.session_secret.get_secret_value())