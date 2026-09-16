import logging

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from sqlalchemy.exc import OperationalError

from app.config import settings
from app.errors import AppError
from app.routers import appointments, chat, dashboard, doctors, patients, symptom_search
from app.services.nvidia_client import NvidiaAPIError

logger = logging.getLogger("app")

app = FastAPI(title="Doctor Appointment Booking API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.exception_handler(AppError)
async def app_error_handler(request: Request, exc: AppError):
    return JSONResponse(status_code=exc.status_code, content={"detail": exc.message})


@app.exception_handler(OperationalError)
async def operational_error_handler(request: Request, exc: OperationalError):
    """Database unreachable, or a SQLite write lock held past busy_timeout.

    Returned as 503 rather than a bare 500 so Cloud Run's load balancer and any client
    retry logic can tell "try again" apart from "this request is broken".
    """
    logger.exception("database unavailable on %s %s", request.method, request.url.path)
    return JSONResponse(status_code=503, content={"detail": "Service temporarily unavailable, please retry."})


@app.exception_handler(NvidiaAPIError)
async def nvidia_error_handler(request: Request, exc: NvidiaAPIError):
    """Upstream NIM failure (missing key, rate limit, model outage).

    502 rather than 500: the failure is upstream, not in this service. Note that
    symptom_match._embedding_match already swallows NvidiaAPIError and falls through to
    "no match", so this handler is really for the /chat path, which has no fallback.
    """
    logger.exception("NVIDIA API failed on %s %s", request.method, request.url.path)
    return JSONResponse(status_code=502, content={"detail": "The assistant is unavailable right now, please retry."})


app.include_router(doctors.router, prefix="/api")
app.include_router(patients.router, prefix="/api")
app.include_router(appointments.router, prefix="/api")
app.include_router(dashboard.router, prefix="/api")
app.include_router(symptom_search.router, prefix="/api")
app.include_router(chat.router, prefix="/api")


@app.get("/api/health")
async def health():
    return {"status": "ok"}
