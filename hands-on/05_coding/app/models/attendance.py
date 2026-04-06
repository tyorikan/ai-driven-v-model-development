from datetime import datetime, date
from decimal import Decimal
from uuid import UUID, uuid4
from sqlalchemy import ForeignKey, DateTime, Numeric, Date, Enum as SAEnum
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.db.session import Base
from app.models.enums import RecordTypeEnum

class AttendanceRecord(Base):
    __tablename__ = "attendance_records"

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    employee_id: Mapped[UUID] = mapped_column(ForeignKey("employees.id"))
    record_type: Mapped[RecordTypeEnum] = mapped_column(SAEnum(RecordTypeEnum))
    event_time: Mapped[datetime] = mapped_column(DateTime)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.now)

    employee: Mapped["Employee"] = relationship(back_populates="attendance_records")

class DailySummary(Base):
    __tablename__ = "daily_summaries"

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    employee_id: Mapped[UUID] = mapped_column(ForeignKey("employees.id"))
    work_date: Mapped[date] = mapped_column(Date)
    total_working_hours: Mapped[Decimal] = mapped_column(Numeric(10, 2))
    overtime_hours: Mapped[Decimal] = mapped_column(Numeric(10, 2))
    midnight_hours: Mapped[Decimal] = mapped_column(Numeric(10, 2))
    break_hours: Mapped[Decimal] = mapped_column(Numeric(10, 2))
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.now)

    employee: Mapped["Employee"] = relationship(back_populates="daily_summaries")
