"""FastAPI Exception Handlers.
Guarantees consistent JSON error envelopes:
{
    "error": {
        "code": "ERROR_CODE",
        "message": "Human readable description",
        "details": {}
    }
}
"""
import logging
from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException

from app.core.exceptions import BugSenseException

logger = logging.getLogger("bugsense.errors")


def register_error_handlers(app: FastAPI) -> None:
    """Register all custom exception handlers to the FastAPI application."""

    @app.exception_handler(BugSenseException)
    async def bugsense_exception_handler(request: Request, exc: BugSenseException):
        logger.warning(
            "Handled BugSenseException: [%s] %s (Path: %s)",
            exc.code,
            exc.message,
            request.url.path,
        )
        return JSONResponse(
            status_code=exc.status_code,
            content={
                "error": {
                    "code": exc.code,
                    "message": exc.message,
                    "details": exc.details,
                }
            },
        )

    @app.exception_handler(RequestValidationError)
    async def validation_exception_handler(request: Request, exc: RequestValidationError):
        logger.warning("Request validation error on %s: %s", request.url.path, exc.errors())
        return JSONResponse(
            status_code=422,
            content={
                "error": {
                    "code": "REQUEST_VALIDATION_ERROR",
                    "message": "The submitted request body or parameters are invalid.",
                    "details": {"validation_errors": exc.errors()},
                }
            },
        )

    @app.exception_handler(StarletteHTTPException)
    async def http_exception_handler(request: Request, exc: StarletteHTTPException):
        return JSONResponse(
            status_code=exc.status_code,
            content={
                "error": {
                    "code": f"HTTP_{exc.status_code}",
                    "message": str(exc.detail),
                    "details": {},
                }
            },
        )

    @app.exception_handler(Exception)
    async def unhandled_exception_handler(request: Request, exc: Exception):
        logger.exception("Unhandled server exception on %s: %s", request.url.path, str(exc))
        return JSONResponse(
            status_code=500,
            content={
                "error": {
                    "code": "INTERNAL_SERVER_ERROR",
                    "message": "An unexpected internal server error occurred. Please contact system admin.",
                    "details": {"exception_type": type(exc).__name__, "hint": str(exc)},
                }
            },
        )
