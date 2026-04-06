from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session
from app.db.session import get_db
from app.schemas.attendance import (
    ClockInRequest, 
    ClockOutRequest, 
    DailySummaryRequest, 
    DailySummaryResponse,
    AttendanceRecordResponse
)
from app.services.attendance_service import AttendanceService

router = APIRouter(prefix="/api/v1/attendance", tags=["attendance"])

# REVIEW FIX: Service をモジュールレベルで保持せず、Depends で注入する
def get_attendance_service() -> AttendanceService:
    return AttendanceService()

@router.post("/clock-in", response_model=AttendanceRecordResponse, status_code=status.HTTP_201_CREATED)
def clock_in(
    req: ClockInRequest, 
    db: Session = Depends(get_db),
    service: AttendanceService = Depends(get_attendance_service)
):
    # REVIEW FIX: service を引数から受け取る
    return service.clock_in(db, req.employee_id, req.clock_in_time)

@router.post("/clock-out", response_model=AttendanceRecordResponse)
def clock_out(
    req: ClockOutRequest, 
    db: Session = Depends(get_db),
    service: AttendanceService = Depends(get_attendance_service)
):
    # REVIEW FIX: service を引数から受け取る
    return service.clock_out(db, req.employee_id, req.clock_out_time)

@router.post("/daily-summary", response_model=DailySummaryResponse)
def get_daily_summary(
    req: DailySummaryRequest, 
    db: Session = Depends(get_db),
    service: AttendanceService = Depends(get_attendance_service)
):
    # REVIEW FIX: service を引数から受け取る
    return service.calculate_daily_summary(db, req.employee_id, req.work_date)
