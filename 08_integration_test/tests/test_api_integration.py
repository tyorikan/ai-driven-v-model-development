"""API 結合テスト（AI 生成 → 人間レビュー済み）。

テスト対象: API エンドポイント間の連携動作
対応する設計書: 03_basic_design/basic_design.md セクション 3（API設計）
"""

from datetime import datetime

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.main import app
from app.db.session import get_db
from app.models.item import Base, InspectionStandard, Item


# ---------- テスト用 DB セットアップ ----------

engine = create_engine("sqlite:///:memory:")
TestSessionLocal = sessionmaker(bind=engine)


def override_get_db():
    db = TestSessionLocal()
    try:
        yield db
    finally:
        db.close()


app.dependency_overrides[get_db] = override_get_db


@pytest.fixture(autouse=True)
def setup_db():
    """各テスト前に DB を初期化し、マスタデータを投入する。"""
    Base.metadata.create_all(engine)
    db = TestSessionLocal()

    # テスト用マスタデータ
    item = Item(
        item_id="BP-001",
        item_name="ブレーキパッド Type-A",
        category="ブレーキパッド",
    )
    std = InspectionStandard(
        id="std-dim-001",
        item_id="BP-001",
        inspection_item_name="外径寸法",
        inspection_type="DIMENSION",
        lower_limit=12.00,
        upper_limit=12.50,
        unit="mm",
    )
    db.add_all([item, std])
    db.commit()
    db.close()

    yield

    Base.metadata.drop_all(engine)


@pytest.fixture()
def client():
    return TestClient(app)


# ---------- シナリオ1: 検査登録フロー（正常系） ----------


class TestInspectionRegistrationFlow:
    """ロット登録 → 検査結果登録 → 検査結果取得 の一連のフローを検証する。"""

    def test_full_flow(self, client: TestClient) -> None:
        """ロット登録→検査登録→結果取得の一連のフローが正常に動作すること。"""
        # Step 1: ロット登録
        lot_response = client.post(
            "/api/v1/lots",
            json={
                "lot_number": "20260401-BP-001",
                "item_id": "BP-001",
                "line_code": "LINE-BP",
                "quantity": 100,
                "manufactured_at": "2026-04-01T08:00:00",
            },
        )
        assert lot_response.status_code == 201
        assert lot_response.json()["lot_number"] == "20260401-BP-001"

        # Step 2: 検査結果登録
        inspection_response = client.post(
            "/api/v1/inspections",
            json={
                "lot_number": "20260401-BP-001",
                "inspection_phase": "IN_PROCESS",
                "inspector_id": "INS-001",
                "details": [
                    {
                        "inspection_standard_id": "std-dim-001",
                        "measured_value": "12.25",
                    }
                ],
            },
        )
        assert inspection_response.status_code == 201
        result = inspection_response.json()
        assert result["result"] == "PASS"
        assert result["details"][0]["judgment"] == "PASS"

        # Step 3: 検査結果取得
        list_response = client.get(
            "/api/v1/inspections",
            params={"lot_number": "20260401-BP-001"},
        )
        assert list_response.status_code == 200
        results = list_response.json()
        assert len(results) == 1
        assert results[0]["lot_number"] == "20260401-BP-001"


# ---------- シナリオ2: エラーケース ----------


class TestErrorCases:
    """API のエラーハンドリングを検証する。"""

    def test_inspection_for_nonexistent_lot(
        self, client: TestClient
    ) -> None:
        """存在しないロットへの検査登録が 404 エラーとなること。"""
        response = client.post(
            "/api/v1/inspections",
            json={
                "lot_number": "99999999-XX-999",
                "inspection_phase": "IN_PROCESS",
                "inspector_id": "INS-001",
                "details": [
                    {
                        "inspection_standard_id": "std-dim-001",
                        "measured_value": "12.25",
                    }
                ],
            },
        )
        assert response.status_code == 404
        assert response.json()["error_code"] == "LOT_NOT_FOUND"

    def test_invalid_lot_format(self, client: TestClient) -> None:
        """不正なフォーマットのロット番号が 422 エラーとなること。"""
        response = client.post(
            "/api/v1/inspections",
            json={
                "lot_number": "invalid-format",
                "inspection_phase": "IN_PROCESS",
                "inspector_id": "INS-001",
                "details": [
                    {
                        "inspection_standard_id": "std-dim-001",
                        "measured_value": "12.25",
                    }
                ],
            },
        )
        assert response.status_code == 422

    def test_get_nonexistent_lot(self, client: TestClient) -> None:
        """存在しないロットの取得が 404 エラーとなること。"""
        response = client.get("/api/v1/lots/99999999-XX-999")
        assert response.status_code == 404


# ---------- シナリオ3: 不合格ケース ----------


class TestFailedInspection:
    """検査不合格時の動作を検証する。"""

    def test_failed_inspection_result(self, client: TestClient) -> None:
        """測定値が基準範囲外の場合、結果が FAIL となること。"""
        # ロット登録
        client.post(
            "/api/v1/lots",
            json={
                "lot_number": "20260401-BP-002",
                "item_id": "BP-001",
                "line_code": "LINE-BP",
                "quantity": 100,
                "manufactured_at": "2026-04-01T08:00:00",
            },
        )

        # 基準範囲外の測定値で検査登録
        response = client.post(
            "/api/v1/inspections",
            json={
                "lot_number": "20260401-BP-002",
                "inspection_phase": "IN_PROCESS",
                "inspector_id": "INS-001",
                "details": [
                    {
                        "inspection_standard_id": "std-dim-001",
                        "measured_value": "13.00",  # 上限 12.50 を超過
                    }
                ],
            },
        )
        assert response.status_code == 201
        result = response.json()
        assert result["result"] == "FAIL"
        assert result["details"][0]["judgment"] == "FAIL"
