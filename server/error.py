from fastapi import Request
from starlette.exceptions import HTTPException
from fastapi.exception_handlers import http_exception_handler

from .common import templates


async def http_error_handler(request: Request, exc: HTTPException):
    if exc.status_code == 404:
        return templates.TemplateResponse(
            request=request, name="error.html", status_code=404, context={"exc": exc}
        )
    return await http_exception_handler(request, exc)