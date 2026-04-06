from datetime import datetime, date, time, timedelta
from typing import Optional, List
from uuid import UUID
from sqlalchemy.orm import Session
from sqlalchemy import and_
from app.models.employee import Employee
from app.models.attendance import AttendanceRecord, DailySummary, RecordTypeEnum
from app.core.exceptions import (
    EmployeeNotFoundError, 
    DuplicateClockInError, 
    ValidationError
)

class AttendanceService:
    def clock_in(self, db: Session, employee_id: UUID, clock_in_time: datetime) -> AttendanceRecord:
        # REVIEW FIX: employee_id の型を UUID に変更
        employee = db.query(Employee).filter(Employee.id == employee_id).first()
        if not employee:
            raise EmployeeNotFoundError(f"Employee {employee_id} not found")

        # 同一日の出勤打刻チェック
        today_start = datetime.combine(clock_in_time.date(), time.min)
        today_end = datetime.combine(clock_in_time.date(), time.max)
        
        existing = db.query(AttendanceRecord).filter(
            and_(
                AttendanceRecord.employee_id == employee_id,
                AttendanceRecord.record_type == RecordTypeEnum.CLOCK_IN,
                AttendanceRecord.event_time >= today_start,
                AttendanceRecord.event_time <= today_end
            )
        ).first()
        
        if existing:
            raise DuplicateClockInError(f"Already clocked in today at {existing.event_time}")

        record = AttendanceRecord(
            employee_id=employee_id,
            record_type=RecordTypeEnum.CLOCK_IN,
            event_time=clock_in_time
        )
        db.add(record)
        db.commit()
        db.refresh(record)
        return record

    def clock_out(self, db: Session, employee_id: UUID, clock_out_time: datetime) -> AttendanceRecord:
        # REVIEW FIX: employee_id の型を UUID に変更
        employee = db.query(Employee).filter(Employee.id == employee_id).first()
        if not employee:
            raise EmployeeNotFoundError(f"Employee {employee_id} not found")

        # 出勤打刻の存在チェック
        today_start = datetime.combine(clock_out_time.date(), time.min)
        today_end = datetime.combine(clock_out_time.date(), time.max)
        
        clock_in_record = db.query(AttendanceRecord).filter(
            and_(
                AttendanceRecord.employee_id == employee_id,
                AttendanceRecord.record_type == RecordTypeEnum.CLOCK_IN,
                AttendanceRecord.event_time >= today_start,
                AttendanceRecord.event_time <= today_end
            )
        ).order_by(AttendanceRecord.event_time.desc()).first()

        if not clock_in_record:
            raise ValidationError("出勤打刻が見つかりません")

        record = AttendanceRecord(
            employee_id=employee_id,
            record_type=RecordTypeEnum.CLOCK_OUT,
            event_time=clock_out_time
        )
        db.add(record)
        # REVIEW FIX: トランザクションの原子性を確保するため、中間 commit を削除
        # db.commit() 
        # db.refresh(record)

        # 日次集計の実行 (取得済みのレコードを渡してクエリを削減)
        self.calculate_daily_summary(db, employee_id, clock_out_time.date(), records_context=[clock_in_record, record])
        
        # 最後に一括で commit
        db.commit()
        db.refresh(record)
        return record

    def calculate_daily_summary(self, db: Session, employee_id: UUID, work_date: date, records_context: Optional[List[AttendanceRecord]] = None) -> DailySummary:
        # REVIEW FIX: employee_id の型を UUID に変更。records_context を受け取れるようにしてクエリを削減
        if records_context is None:
            start_of_day = datetime.combine(work_date, time.min)
            end_of_day = datetime.combine(work_date, time.max)
            
            records = db.query(AttendanceRecord).filter(
                and_(
                    AttendanceRecord.employee_id == employee_id,
                    AttendanceRecord.event_time >= start_of_day,
                    AttendanceRecord.event_time <= end_of_day
                )
            ).order_by(AttendanceRecord.event_time.asc()).all()
        else:
            records = sorted(records_context, key=lambda x: x.event_time)

        # REVIEW FIX: 複数回の打刻ペアに対応できるようにロジックを改善
        clock_in_time = None
        logic_results = []
        
        for r in records:
            if r.record_type == RecordTypeEnum.CLOCK_IN:
                clock_in_time = r.event_time
            elif r.record_type == RecordTypeEnum.CLOCK_OUT and clock_in_time:
                logic_results.append(self._calculate_logic(clock_in_time, r.event_time))
                clock_in_time = None

        if not logic_results:
             return None

        # 各セグメントの集計
        total_working_hours = sum(res["total_working_hours"] for res in logic_results)
        total_break_hours = sum(res["break_hours"] for res in logic_results)
        total_midnight_hours = sum(res["midnight_hours"] for res in logic_results)
        
        # 法定残業 (1日の実労働合計が8h超)
        overtime_hours = max(0.0, total_working_hours - 8.0)
        
        summary = db.query(DailySummary).filter(
            and_(DailySummary.employee_id == employee_id, DailySummary.work_date == work_date)
        ).first()
        
        if not summary:
            summary = DailySummary(employee_id=employee_id, work_date=work_date)
            db.add(summary)

        summary.total_working_hours = total_working_hours
        summary.overtime_hours = overtime_hours
        summary.midnight_hours = total_midnight_hours
        summary.break_hours = total_break_hours
        
        # clock_out から呼ばれた場合は上位で commit するため、ここでは commit しない
        if records_context is None:
            db.commit()
            db.refresh(summary)
        return summary

    def _calculate_logic(self, clock_in: datetime, clock_out: datetime) -> dict:
        if clock_out < clock_in:
            raise ValidationError("退勤時刻が出勤時刻より前です")

        duration_sec = (clock_out - clock_in).total_seconds()
        duration_hours = duration_sec / 3600.0

        # 法定基準（6h超で45分、8h超で1時間）を厳密に適用
        if duration_hours > 8.0:
            break_hours = 1.0
        elif duration_hours > 6.0:
            break_hours = 0.75
        else:
            break_hours = 0.0

        actual_working_hours = max(0.0, duration_hours - break_hours)
        
        # 深夜時間の計算 (22:00 - 05:00)
        midnight_hours = self._calculate_midnight_hours(clock_in, clock_out)

        return {
            "total_working_hours": actual_working_hours,
            "break_hours": break_hours,
            "midnight_hours": midnight_hours
        }

    def _calculate_midnight_hours(self, clock_in: datetime, clock_out: datetime) -> float:
        # REVIEW FIX: 0:00-5:00 と 22:00-24:00 (翌5:00) の両方を考慮する
        midnight_total = 0.0
        
        # 1. 当日 0:00 - 5:00
        start_of_day_00 = datetime.combine(clock_in.date(), time.min)
        start_of_day_05 = datetime.combine(clock_in.date(), time(5, 0))
        overlap_start1 = max(clock_in, start_of_day_00)
        overlap_end1 = min(clock_out, start_of_day_05)
        if overlap_start1 < overlap_end1:
            midnight_total += (overlap_end1 - overlap_start1).total_seconds()
            
        # 2. 当日 22:00 - 翌日 5:00
        day_22 = datetime.combine(clock_in.date(), time(22, 0))
        next_day_05 = datetime.combine(clock_in.date() + timedelta(days=1), time(5, 0))
        overlap_start2 = max(clock_in, day_22)
        overlap_end2 = min(clock_out, next_day_05)
        if overlap_start2 < overlap_end2:
            midnight_total += (overlap_end2 - overlap_start2).total_seconds()
            
        return midnight_total / 3600.0

    def calculate_flex_monthly_overtime(self, total_actual_hours: float, work_days: int) -> float:
        prescribed_hours = work_days * 8.0
        return max(0, total_actual_hours - prescribed_hours)
