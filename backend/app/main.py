from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.errors import AppError
from app.routers import appointments, dashboard, doctors, patients, symptom_search

app = FastAPI(title="Doctor Appointment Booking API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.exception_handler(AppError)
async def app_error_handler(request: Request, exc: AppError):
    return JSONResponse(status_code=exc.status_code, content={"detail": exc.message})


app.include_router(doctors.router, prefix="/api")
app.include_router(patients.router, prefix="/api")
app.include_router(appointments.router, prefix="/api")
app.include_router(dashboard.router, prefix="/api")
app.include_router(symptom_search.router, prefix="/api")


@app.get("/api/health")
async def health():
    return {"status": "ok"}
