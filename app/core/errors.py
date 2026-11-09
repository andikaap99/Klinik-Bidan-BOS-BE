"""Seluruh response adalah JSON object; error memakai bentuk {code, message}.

Kode error mengikuti api_contract.md. Endpoint yang bisa memakai ApiError
langsung; handler bawaan menanam ulang validation 422 dan HTTPException.
"""

import logging

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException

logger = logging.getLogger(__name__)


class ApiError(Exception):
    """Golongan error kustom yang dibentuk langsung ke envelope kontrak."""

    def __init__(self, code: str, message: str, status_code: int = 400):
        self.code = code
        self.message = message
        self.status_code = status_code
        super().__init__(message)


def error_response(status_code: int, code: str, message: str) -> JSONResponse:
    return JSONResponse(
        status_code=status_code,
        content={"code": code, "message": message},
    )


_STATUS_TO_CODE: dict[int, str] = {
    400: "BAD_REQUEST",
    401: "INVALID_CREDENTIALS",
    403: "FORBIDDEN",
    404: "NOT_FOUND",
    405: "METHOD_NOT_ALLOWED",
    409: "CONFLICT",
    422: "VALIDATION_ERROR",
    500: "INTERNAL_ERROR",
}


def register_exception_handlers(app: FastAPI) -> None:
    @app.exception_handler(ApiError)
    async def handle_api_error(
        request: Request, exc: ApiError
    ) -> JSONResponse:
        return error_response(exc.status_code, exc.code, exc.message)

    @app.exception_handler(RequestValidationError)
    async def handle_validation_error(
        request: Request, exc: RequestValidationError
    ) -> JSONResponse:
        # Pesan disengaja digeneralisasi agar tidak membocorkan aturan internal
        return error_response(422, "VALIDATION_ERROR", "Isi request tidak valid")

    @app.exception_handler(StarletteHTTPException)
    async def handle_http_exception(
        request: Request, exc: StarletteHTTPException
    ) -> JSONResponse:
        code = _STATUS_TO_CODE.get(exc.status_code, "HTTP_ERROR")
        message = str(exc.detail) if exc.detail is not None else "Request tidak valid"
        return error_response(exc.status_code, code, message)

    @app.exception_handler(Exception)
    async def handle_unhandled_exception(
        request: Request, exc: Exception
    ) -> JSONResponse:
        logger.exception("Unhandled exception pada %s %s", request.method, request.url.path)
        return error_response(500, "INTERNAL_ERROR", "Terjadi kesalahan internal")
