from datetime import datetime

from pydantic import BaseModel, ConfigDict, EmailStr, Field

from app.models import AppointmentStatus, SlotStatus


class DoctorOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    specialty: str
    bio: str
    experience_years: int
    consultation_duration_minutes: int


class DoctorWithNextSlot(DoctorOut):
    next_available_slot: datetime | None = None


class SlotOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    doctor_id: int
    start_datetime: datetime
    end_datetime: datetime
    status: SlotStatus
    recommended: bool = False


class PatientOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    email: str
    phone: str


class PatientCreate(BaseModel):
    name: str = Field(min_length=1, max_length=120)
    email: EmailStr
    phone: str = ""


class AppointmentCreate(BaseModel):
    slot_id: int
    patient_id: int
    reason: str = ""


class AppointmentOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    slot_id: int
    patient_id: int
    doctor_id: int
    status: AppointmentStatus
    reason: str
    created_at: datetime
    cancelled_at: datetime | None
    slot: SlotOut
    doctor: DoctorOut
    patient: PatientOut


class AppointmentStatusUpdate(BaseModel):
    status: AppointmentStatus


class SymptomSearchRequest(BaseModel):
    text: str = Field(min_length=1, max_length=500)


class SymptomSearchResponse(BaseModel):
    emergency: bool
    specialty: str | None
    source: str
    message: str | None
    matched_phrase: str | None = None


class ChatMessage(BaseModel):
    role: str
    content: str


class ChatRequest(BaseModel):
    message: str = Field(min_length=1, max_length=1000)
    conversation_history: list[ChatMessage] = Field(default_factory=list)
    patient_id: int


class ToolEventOut(BaseModel):
    tool: str
    arguments: dict
    result: dict | list


class ChatResponse(BaseModel):
    reply: str
    tool_events: list[ToolEventOut] = Field(default_factory=list)
