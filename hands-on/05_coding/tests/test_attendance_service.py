import pytest
from datetime import datetime, date, time, timedelta
from uuid import uuid4
from decimal import Decimal
from app.services.attendance_service import AttendanceService
from app.core.exceptions import ValidationError, DuplicateClockInError, EmployeeNotFoundError
from app.models.employee import Employee
from app.models.attendance import RecordTypeEnum

@pytest.fixture
def service():
    return AttendanceService()

@pytest.fixture
def target_employee_id():
    return uuid4()

class TestCalculateDailySummarySuccess:
    """正常系テスト: 勤務時間計算ロジックの検証"""

    def test_fixed_standard_work(self, service):
        """1. 固定時間制: 定時退勤（9:00〜18:00）→ 実働8h、休憩1h"""
        clock_in = datetime(2026, 4, 6, 9, 0)
        clock_out = datetime(2026, 4, 6, 18, 0)
        
        summary = service._calculate_logic(clock_in, clock_out)
        
        assert summary["total_working_hours"] == 8.0
        assert summary["break_hours"] == 1.0
        assert summary["midnight_hours"] == 0.0

    def test_fixed_with_overtime(self, service):
        """2. 固定時間制: 2時間残業（9:00〜20:00）→ 実働10h（休憩1h含む）"""
        clock_in = datetime(2026, 4, 6, 9, 0)
        clock_out = datetime(2026, 4, 6, 20, 0)
        
        summary = service._calculate_logic(clock_in, clock_out)
        
        assert summary["total_working_hours"] == 10.0
        assert summary["break_hours"] == 1.0

    def test_fixed_with_midnight(self, service):
        """3. 固定時間制: 深夜残業あり（9:00〜23:30）→ 深夜1.5h"""
        clock_in = datetime(2026, 4, 6, 9, 0)
        clock_out = datetime(2026, 4, 6, 23, 30)
        
        summary = service._calculate_logic(clock_in, clock_out)
        
        assert summary["total_working_hours"] == 13.5
        assert summary["midnight_hours"] == 1.5
        assert summary["break_hours"] == 1.0

    def test_early_morning_midnight(self, service):
        """3b. 早朝深夜: 4:00〜9:00 → 深夜1.0h (0:00-5:00の枠)"""
        clock_in = datetime(2026, 4, 6, 4, 0)
        clock_out = datetime(2026, 4, 6, 9, 0)
        
        summary = service._calculate_logic(clock_in, clock_out)
        assert summary["midnight_hours"] == 1.0

    def test_multi_segment_summary(self, service):
        """3c. 複数セグメント: 9:00-12:00, 13:00-19:00 → 実働9h、残業1h"""
        from app.models.attendance import AttendanceRecord, RecordTypeEnum, DailySummary
        from uuid import uuid4
        from unittest.mock import MagicMock
        emp_id = uuid4()
        records = [
            AttendanceRecord(employee_id=emp_id, record_type=RecordTypeEnum.CLOCK_IN, event_time=datetime(2026, 4, 6, 9, 0)),
            AttendanceRecord(employee_id=emp_id, record_type=RecordTypeEnum.CLOCK_OUT, event_time=datetime(2026, 4, 6, 12, 0)),
            AttendanceRecord(employee_id=emp_id, record_type=RecordTypeEnum.CLOCK_IN, event_time=datetime(2026, 4, 6, 13, 0)),
            AttendanceRecord(employee_id=emp_id, record_type=RecordTypeEnum.CLOCK_OUT, event_time=datetime(2026, 4, 6, 19, 0)),
        ]
        
        # db の動作をモック
        mock_db = MagicMock()
        mock_db.query.return_value.filter.return_value.first.return_value = None # 既存サマリーなし
        
        summary = service.calculate_daily_summary(mock_db, emp_id, date(2026, 4, 6), records_context=records)
        
        assert summary.total_working_hours == 9.0
        assert summary.overtime_hours == 1.0

    def test_flex_monthly_overtime(self, service):
        """4. フレックス制: 月次集計で残業計算（総実労働175h、所定20日 → 残業15h）"""
        total_actual_hours = 175.0
        work_days = 20
        
        overtime = service.calculate_flex_monthly_overtime(total_actual_hours, work_days)
        assert overtime == 15.0

class TestAdditionalSuccess:
    """追加正常系テスト"""

    def test_short_work(self, service):
        """1. 短時間勤務（4時間: 9:00-13:00）→ 実働4h、休憩0h、残業0h"""
        clock_in = datetime(2026, 4, 6, 9, 0)
        clock_out = datetime(2026, 4, 6, 13, 0)
        res = service._calculate_logic(clock_in, clock_out)
        assert Decimal(str(res["total_working_hours"])) == Decimal("4.0")
        assert Decimal(str(res["break_hours"])) == Decimal("0.0")

    def test_over_6_hours_stay(self, service):
        """2. ちょうど6時間超の勤務（9:00-15:30、拘束6.5h）→ 休憩45分控除、実働5.75h"""
        clock_in = datetime(2026, 4, 6, 9, 0)
        clock_out = datetime(2026, 4, 6, 15, 30)
        res = service._calculate_logic(clock_in, clock_out)
        assert Decimal(str(res["break_hours"])) == Decimal("0.75")
        assert Decimal(str(res["total_working_hours"])) == Decimal("5.75")

    def test_flex_exactly_prescribed(self, service):
        """3. フレックス制: 月の総実労働が所定時間ちょうど → 残業0h"""
        overtime = service.calculate_flex_monthly_overtime(160.0, 20)
        assert Decimal(str(overtime)) == Decimal("0.0")

    def test_flex_under_prescribed(self, service):
        """4. フレックス制: 月の総実労働が所定時間未満 → 残業0h"""
        overtime = service.calculate_flex_monthly_overtime(150.0, 20)
        assert Decimal(str(overtime)) == Decimal("0.0")

class TestAdditionalBoundary:
    """追加境界値テスト"""

    def test_exactly_8_hours_stay(self, service):
        """5. 拘束時間ちょうど8時間（9:00-17:00）→ 休憩45分控除、実働7.25h、残業0h"""
        clock_in = datetime(2026, 4, 6, 9, 0)
        clock_out = datetime(2026, 4, 6, 17, 0)
        res = service._calculate_logic(clock_in, clock_out)
        assert Decimal(str(res["break_hours"])) == Decimal("0.75")
        assert Decimal(str(res["total_working_hours"])) == Decimal("7.25")

    def test_over_8_hours_stay(self, service):
        """6. 拘束時間8時間1分（9:00-17:01）→ 休憩60分控除"""
        clock_in = datetime(2026, 4, 6, 9, 0)
        clock_out = datetime(2026, 4, 6, 17, 1)
        res = service._calculate_logic(clock_in, clock_out)
        assert Decimal(str(res["break_hours"])) == Decimal("1.0")
        expected_work = Decimal("7") + Decimal("1") / Decimal("60")
        assert Decimal(str(res["total_working_hours"])).quantize(Decimal("0.000001")) == expected_work.quantize(Decimal("0.000001"))

class TestAttendanceErrors:
    """異常系テスト: 不正な打刻パターンの検証"""

    def test_clock_out_before_clock_in(self, service):
        """5. 退勤時刻が出勤時刻より前 → ValidationError"""
        clock_in = datetime(2026, 4, 6, 18, 0)
        clock_out = datetime(2026, 4, 6, 9, 0)
        
        with pytest.raises(ValidationError) as excinfo:
            service._calculate_logic(clock_in, clock_out)
        assert "退勤時刻が出勤時刻より前です" in str(excinfo.value)

class TestWorkingHoursBoundary:
    """境界値テスト: 休憩時間と深夜時間の切り替わり検証"""

    def test_exactly_8_hours_work(self, service):
        """8. ちょうど8時間勤務（9:00-18:00、休憩1h）"""
        clock_in = datetime(2026, 4, 6, 9, 0)
        clock_out = datetime(2026, 4, 6, 18, 0)
        res = service._calculate_logic(clock_in, clock_out)
        assert Decimal(str(res["total_working_hours"])) == Decimal("8.0")

    def test_just_over_8_hours(self, service):
        """9. 8時間1分勤務（9:00-18:01）"""
        clock_in = datetime(2026, 4, 6, 9, 0)
        clock_out = datetime(2026, 4, 6, 18, 1)
        res = service._calculate_logic(clock_in, clock_out)
        assert Decimal(str(res["total_working_hours"])) > Decimal("8.0")

    def test_midnight_boundary_exactly(self, service):
        """10. ちょうど22:00退勤 → 深夜0h"""
        clock_in = datetime(2026, 4, 6, 13, 0)
        clock_out = datetime(2026, 4, 6, 22, 0)
        res = service._calculate_logic(clock_in, clock_out)
        assert Decimal(str(res["midnight_hours"])) == Decimal("0.0")

    def test_midnight_boundary_just_over(self, service):
        """11. 22:01退勤 → 深夜 > 0"""
        clock_in = datetime(2026, 4, 6, 13, 0)
        clock_out = datetime(2026, 4, 6, 22, 1)
        res = service._calculate_logic(clock_in, clock_out)
        assert Decimal(str(res["midnight_hours"])) > Decimal("0.0")

    def test_break_exactly_6_hours(self, service):
        """12. 6時間ちょうど勤務（9:00-15:00）→ 休憩控除なし"""
        clock_in = datetime(2026, 4, 6, 9, 0)
        clock_out = datetime(2026, 4, 6, 15, 0)
        res = service._calculate_logic(clock_in, clock_out)
        assert Decimal(str(res["break_hours"])) == Decimal("0.0")
        assert Decimal(str(res["total_working_hours"])) == Decimal("6.0")

    def test_break_just_over_6_hours(self, service):
        """13. 6時間超勤務（9:00-15:01）→ 45分控除されることを確認（ステップ型控除）"""
        clock_in = datetime(2026, 4, 6, 9, 0)
        clock_out = datetime(2026, 4, 6, 15, 1)
        res = service._calculate_logic(clock_in, clock_out)
        
        # 6h1m stay -> 45m (0.75h) break
        assert Decimal(str(res["break_hours"])) == Decimal("0.75")
        # (6 + 1/60) - 0.75 = 5.2666...
        expected_work = (Decimal("6") + Decimal("1") / Decimal("60")) - Decimal("0.75")
        assert Decimal(str(res["total_working_hours"])).quantize(Decimal("0.001")) == expected_work.quantize(Decimal("0.001"))
