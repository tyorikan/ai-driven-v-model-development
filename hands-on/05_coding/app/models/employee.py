from datetime import date, datetime
from typing import List
from uuid import UUID, uuid4
from sqlalchemy import String, Date, DateTime, Boolean, Enum as SAEnum
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.db.session import Base
from app.models.enums import RoleEnum, EmploymentTypeEnum

class Employee(Base):
    __tablename__ = "employees"

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    last_name: Mapped[str] = mapped_column(String(50))
    first_name: Mapped[str] = mapped_column(String(50))
    email: Mapped[str] = mapped_column(String(255), unique=True, index=True)
    role: Mapped[RoleEnum] = mapped_column(SAEnum(RoleEnum))
    employment_type: Mapped[EmploymentTypeEnum] = mapped_column(SAEnum(EmploymentTypeEnum))
    joined_date: Mapped[date] = mapped_column(Date)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.now)

    attendance_records: Mapped[List["AttendanceRecord"]] = relationship(back_populates="employee")
    daily_summaries: Mapped[List["DailySummary"]] = relationship(back_populates="employee")
