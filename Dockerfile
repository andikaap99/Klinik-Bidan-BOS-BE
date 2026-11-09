# syntax=docker/dockerfile:1
# Tunggal untuk dev (compose) & prod. Prod: CMD default `fastapi run`.
# Dev: compose menimpa command dengan `fastapi dev`.

FROM python:3.12-slim

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    UV_COMPILE_BYTECODE=1 \
    UV_LINK_MODE=copy \
    PATH=/app/.venv/bin:$PATH

WORKDIR /app

# uv binary (penting: versinya selaras dengan uv.lock, lihat pyproject/uv.lock)
COPY --from=ghcr.io/astral-sh/uv:0.11.16 /uv /uvx /bin/

# Layer dependensi dulu supaya cache build tidak hangus saat kode berubah
COPY pyproject.toml uv.lock ./
# tool.uv package = false, cukup sync dependensi. Tanpa dev group (pytest/ruff
# dipakai di host, bukan di dalam image)
RUN uv sync --frozen --no-dev

COPY app ./app

# Prod default: fastapi run (uvicorn tanpa reload)
CMD ["fastapi", "run", "--host", "0.0.0.0", "--port", "8000"]
