import enum
from datetime import datetime

from sqlalchemy import (
    DateTime,
    Enum,
    ForeignKey,
    Integer,
    String,
    Text,
    Time,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base
from app.utils import utc_now


class SlotStatus(str, enum.Enum):
    open = "open"
    booked = "booked"
    blocked = "blocked"


class AppointmentStatus(str, enum.Enum):
    confirmed = "confirmed"
    cancelled = "cancelled"
    completed = "completed"
    no_show = "no_show"


# Only these transitions are legal out of `confirmed`; every other status is terminal.
VALID_APPOINTMENT_TRANSITIONS = {
    AppointmentStatus.confirmed: {
        AppointmentStatus.cancelled,
        AppointmentStatus.completed,
        AppointmentStatus.no_show,
    },
}


class Doctor(Base):
    __tablename__ = "doctors"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String(120), nullable=False)
    specialty: Mapped[str] = mapped_column(String(80), nullable=False, index=True)
    bio: Mapped[str] = mapped_column(Text, default="")
    experience_years: Mapped[int] = mapped_column(Integer, default=0)
    consultation_duration_minutes: Mapped[int] = mapped_column(Integer, default=30)

    availability: Mapped[list["DoctorAvailability"]] = relationship(
        back_populates="doctor", cascade="all, delete-orphan"
    )
    slots: Mapped[list["Slot"]] = relationship(back_populates="doctor")


class DoctorAvailability(Base):
    __tablename__ = "doctor_availability"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    doctor_id: Mapped[int] = mapped_column(ForeignKey("doctors.id"), nullable=False)
    day_of_week: Mapped[int] = mapped_column(Integer, nullable=False)  # 0=Mon .. 6=Sun
    start_time: Mapped[str] = mapped_column(Time, nullable=False)
    end_time: Mapped[str] = mapped_column(Time, nullable=False)

    doctor: Mapped["Doctor"] = relationship(back_populates="availability")


class Slot(Base):
    __tablename__ = "slots"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    doctor_id: Mapped[int] = mapped_column(ForeignKey("doctors.id"), nullable=False)
    start_datetime: Mapped[datetime] = mapped_column(DateTime, nullable=False, index=True)
    end_datetime: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    status: Mapped[SlotStatus] = mapped_column(
        Enum(SlotStatus), default=SlotStatus.open, nullable=False, index=True
    )

    doctor: Mapped["Doctor"] = relationship(back_populates="slots")
    appointment: Mapped["Appointment | None"] = relationship(back_populates="slot")


class Patient(Base):
    __tablename__ = "patients"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String(120), nullable=False)
    email: Mapped[str] = mapped_column(String(180), nullable=False, unique=True)
    phone: Mapped[str] = mapped_column(String(20), default="")


class Appointment(Base):
    __tablename__ = "appointments"
    __table_args__ = (UniqueConstraint("slot_id", name="uq_appointments_slot_id"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    slot_id: Mapped[int] = mapped_column(ForeignKey("slots.id"), nullable=False)
    patient_id: Mapped[int] = mapped_column(ForeignKey("patients.id"), nullable=False)
    doctor_id: Mapped[int] = mapped_column(ForeignKey("doctors.id"), nullable=False)
    status: Mapped[AppointmentStatus] = mapped_column(
        Enum(AppointmentStatus), default=AppointmentStatus.confirmed, nullable=False, index=True
    )
    reason: Mapped[str] = mapped_column(Text, default="")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utc_now)
    cancelled_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)

    slot: Mapped["Slot"] = relationship(back_populates="appointment")
    patient: Mapped["Patient"] = relationship()
    doctor: Mapped["Doctor"] = relationship()
