# Cloud Run image for the FastAPI backend.
# Build context is ./backend (not the project root) — nothing outside backend/ is needed.
#
#   docker build -t appt-backend:local ./backend

FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1

# app/utils.py deliberately uses naive LOCAL wall-clock time (datetime.now()) to match the
# clinic-local slot timestamps in seed.py. Containers default to UTC, which would put every
# "is this slot in the past" and cancellation-window check 5h30m out in IST. Pinning TZ here
# is what makes that design hold in a container; commands.md sets it on the service too.
ENV TZ=Asia/Kolkata

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY app ./app
COPY scripts ./scripts

# The Chroma taxonomy index is baked in, not built at startup or mounted. It's written once
# by `python -m app.embed_taxonomy` (an NVIDIA embeddings call over ~76 fixed phrases) and is
# read-only afterwards, so rebuilding it per cold start would burn an API call and add latency
# for an identical result. It must exist locally before you build — see commands.md step 2.
# Chroma's SQLite/HNSW files also don't behave reliably over a GCS FUSE mount, which rules out
# the volume-mount alternative. Trade-off: re-run embed_taxonomy and rebuild when
# app/taxonomy.py changes.
COPY chroma_data ./chroma_data

RUN adduser --disabled-password --gecos "" appuser \
    && chown -R appuser:appuser /app
USER appuser

# Cloud Run injects PORT and ignores EXPOSE; 8080 is the default it sets.
ENV PORT=8080
EXPOSE 8080

# One worker per container. Scale with --max-instances, not --workers: the SQLite
# BEGIN IMMEDIATE path in app/database.py does not tolerate multiple processes on
# one file, and on Postgres each worker would open its own connection pool.
CMD exec uvicorn app.main:app --host 0.0.0.0 --port ${PORT} --workers 1
