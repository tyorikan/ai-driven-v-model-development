import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool
from datetime import datetime, date
import uuid
from app.main import app
from app.db.session import Base, get_db
from app.models.employee import Employee
from app.models.attendance import AttendanceRecord, DailySummary
from app.models.enums import RoleEnum, EmploymentTypeEnum

# SQLite インメモリ DB と StaticPool を使用して、テスト期間中の接続を維持する
SQLALCHEMY_DATABASE_URL = "sqlite:///:memory:"

engine = create_engine(
    SQLALCHEMY_DATABASE_URL,
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

@pytest.fixture
def db_session():
    # テーブル作成
    Base.metadata.create_all(bind=engine)
    session = TestingSessionLocal()
    try:
        yield session
    finally:
        session.close()
        # テーブル削除
        Base.metadata.drop_all(bind=engine)

@pytest.fixture
def client(db_session):
    def override_get_db():
        try:
            yield db_session
        finally:
            pass
    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app) as c:
        yield c
    app.dependency_overrides.clear()

@pytest.fixture
def sample_employee(db_session):
    employee = Employee(
        last_name="山田",
        first_name="太郎",
        email="test@example.com",
        role=RoleEnum.GENERAL,
        employment_type=EmploymentTypeEnum.REGULAR,
        joined_date=date(2024, 1, 1)
    )
    db_session.add(employee)
    db_session.commit()
    db_session.refresh(employee)
    return employee

class TestAPIIntegration:
    """API 結合テスト: 正常フローと基本的なエラーハンドリング"""

    def test_full_attendance_flow(self, client, sample_employee):
        """出勤打刻 → 退勤打刻 → 日次集計の一連フローが正しく動作することを確認"""
        emp_id = str(sample_employee.id)
        
        # 1. 出勤
        clock_in_res = client.post("/api/v1/attendance/clock-in", json={
            "employee_id": emp_id,
            "clock_in_time": "2026-04-06T09:00:00"
        })
        assert clock_in_res.status_code == 201

        # 2. 退勤
        clock_out_res = client.post("/api/v1/attendance/clock-out", json={
            "employee_id": emp_id,
            "clock_out_time": "2026-04-06T18:00:00"
        })
        assert clock_out_res.status_code == 200

        # 3. 日次集計
        summary_res = client.post("/api/v1/attendance/daily-summary", json={
            "employee_id": emp_id,
            "work_date": "2026-04-06"
        })
        assert summary_res.status_code == 200
        data = summary_res.json()
        assert data["total_working_hours"] == 8.0
        assert data["overtime_hours"] == 0.0

    def test_duplicate_clock_in(self, client, sample_employee):
        """同一日に二重で出勤打刻をした場合に 409 Conflict エラーが返ることを確認"""
        emp_id = str(sample_employee.id)
        client.post("/api/v1/attendance/clock-in", json={
            "employee_id": emp_id,
            "clock_in_time": "2026-04-06T09:00:00"
        })
        res = client.post("/api/v1/attendance/clock-in", json={
            "employee_id": emp_id,
            "clock_in_time": "2026-04-06T10:00:00"
        })
        assert res.status_code == 409
        assert res.json()["error_code"] == "DUPLICATE_CLOCK_IN"

    def test_not_found_employee(self, client):
        """存在しない従業員IDで打刻を試みた場合に 404 Not Found エラーが返ることを確認"""
        res = client.post("/api/v1/attendance/clock-in", json={
            "employee_id": str(uuid.uuid4()),
            "clock_in_time": "2026-04-06T09:00:00"
        })
        assert res.status_code == 404
        assert res.json()["error_code"] == "EMPLOYEE_NOT_FOUND"

    def test_clock_out_without_clock_in(self, client, sample_employee):
        """出勤打刻がない状態で退勤打刻を試みた場合に 400 Bad Request エラーが返ることを確認"""
        emp_id = str(sample_employee.id)
        res = client.post("/api/v1/attendance/clock-out", json={
            "employee_id": emp_id,
            "clock_out_time": "2026-04-06T18:00:00"
        })
        assert res.status_code == 400
        assert res.json()["error_code"] == "VALIDATION_ERROR"

class TestApiBoundaryScenarios:
    """シナリオ3: 境界値の API レベル検証"""

    def test_standard_work_hours(self, client, sample_employee):
        """定時勤務（9:00-18:00）で残業が0時間であることを確認"""
        emp_id = str(sample_employee.id)
        client.post("/api/v1/attendance/clock-in", json={"employee_id": emp_id, "clock_in_time": "2026-04-06T09:00:00"})
        client.post("/api/v1/attendance/clock-out", json={"employee_id": emp_id, "clock_out_time": "2026-04-06T18:00:00"})
        
        res = client.post("/api/v1/attendance/daily-summary", json={"employee_id": emp_id, "work_date": "2026-04-06"})
        assert res.status_code == 200
        assert res.json()["overtime_hours"] == 0.0
        assert res.json()["total_working_hours"] == 8.0

    def test_overtime_work_hours(self, client, sample_employee):
        """残業勤務（9:00-20:00）で残業が2時間発生することを確認"""
        emp_id = str(sample_employee.id)
        client.post("/api/v1/attendance/clock-in", json={"employee_id": emp_id, "clock_in_time": "2026-04-06T09:00:00"})
        client.post("/api/v1/attendance/clock-out", json={"employee_id": emp_id, "clock_out_time": "2026-04-06T20:00:00"})
        
        res = client.post("/api/v1/attendance/daily-summary", json={"employee_id": emp_id, "work_date": "2026-04-06"})
        assert res.status_code == 200
        assert res.json()["overtime_hours"] == 2.0
        assert res.json()["total_working_hours"] == 10.0

    def test_midnight_work_hours(self, client, sample_employee):
        """深夜勤務（9:00-23:30）で深夜労働が1.5時間発生することを確認"""
        emp_id = str(sample_employee.id)
        client.post("/api/v1/attendance/clock-in", json={"employee_id": emp_id, "clock_in_time": "2026-04-06T09:00:00"})
        client.post("/api/v1/attendance/clock-out", json={"employee_id": emp_id, "clock_out_time": "2026-04-06T23:30:00"})
        
        res = client.post("/api/v1/attendance/daily-summary", json={"employee_id": emp_id, "work_date": "2026-04-06"})
        assert res.status_code == 200
        assert res.json()["midnight_hours"] == 1.5

class TestApiErrorResponses:
    """シナリオ4: エラーレスポンスの検証"""

    def test_error_response_format_and_codes(self, client, sample_employee):
        """エラーレスポンスの形式が統一されており、適切な error_code が含まれることを確認"""
        emp_id = str(sample_employee.id)

        # 404: EMPLOYEE_NOT_FOUND
        res_404 = client.post("/api/v1/attendance/clock-in", json={
            "employee_id": str(uuid.uuid4()),
            "clock_in_time": "2026-04-06T09:00:00"
        })
        assert res_404.status_code == 404
        body_404 = res_404.json()
        assert body_404["error_code"] == "EMPLOYEE_NOT_FOUND"
        assert "detail" in body_404

        # 409: DUPLICATE_CLOCK_IN
        client.post("/api/v1/attendance/clock-in", json={"employee_id": emp_id, "clock_in_time": "2026-04-06T09:00:00"})
        res_409 = client.post("/api/v1/attendance/clock-in", json={"employee_id": emp_id, "clock_in_time": "2026-04-06T10:00:00"})
        assert res_409.status_code == 409
        body_409 = res_409.json()
        assert body_409["error_code"] == "DUPLICATE_CLOCK_IN"
        assert "detail" in body_409

        # 400: VALIDATION_ERROR (出勤なしの退勤)
        res_400 = client.post("/api/v1/attendance/clock-out", json={
            "employee_id": emp_id,
            "clock_out_time": "2026-04-07T18:00:00" 
        })
        assert res_400.status_code == 400
        body_400 = res_400.json()
        assert body_400["error_code"] == "VALIDATION_ERROR"
        assert "detail" in body_400
