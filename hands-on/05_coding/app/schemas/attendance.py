from datetime import datetime, date
from decimal import Decimal
from typing import Optional
from uuid import UUID
from pydantic import BaseModel, ConfigDict, Field

class ClockInRequest(BaseModel):
    employee_id: UUID
    # REVIEW FIX: 使用されていない location を削除
    clock_in_time: datetime = Field(default_factory=datetime.now)

class ClockOutRequest(BaseModel):
    employee_id: UUID
    clock_out_time: datetime = Field(default_factory=datetime.now)

class DailySummaryRequest(BaseModel):
    employee_id: UUID
    work_date: date

class DailySummaryResponse(BaseModel):
    work_date: date
    total_working_hours: float
    overtime_hours: float
    midnight_hours: float
    break_hours: float

    model_config = ConfigDict(from_attributes=True)

class AttendanceRecordResponse(BaseModel):
    id: UUID
    employee_id: UUID
    record_type: str
    event_time: datetime

    model_config = ConfigDict(from_attributes=True)

class ErrorResponse(BaseModel):
    error_code: str
    detail: str
