"""InspectionService の単体テスト（AI 生成 → 人間レビュー済み）。

テスト対象: app/services/inspection_service.py
対応する設計書: 04_detailed_design/detailed_design.md セクション 3.1
"""

from decimal import Decimal

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from app.core.exceptions import DuplicateException, NotFoundException
from app.models.item import Base, InspectionStandard, Item
from app.models.lot import Lot
from app.schemas.inspection import InspectionCreate, InspectionDetailCreate
from app.services.inspection_service import InspectionService


# ---------- フィクスチャ ----------


@pytest.fixture()
def db_session() -> Session:
    """テスト用のインメモリ SQLite セッションを生成する。"""
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    session = sessionmaker(bind=engine)()
    yield session
    session.close()


@pytest.fixture()
def sample_data(db_session: Session) -> dict:
    """テスト用のマスタデータとロットを投入する。"""
    # 品目マスタ
    item = Item(
        item_id="BP-001",
        item_name="ブレーキパッド Type-A",
        category="ブレーキパッド",
    )
    db_session.add(item)

    # 検査基準（外径寸法: 12.00〜12.50mm）
    std_dimension = InspectionStandard(
        id="std-dim-001",
        item_id="BP-001",
        inspection_item_name="外径寸法",
        inspection_type="DIMENSION",
        lower_limit=12.00,
        upper_limit=12.50,
        unit="mm",
    )
    # 検査基準（硬度: 80〜95 HRC）
    std_hardness = InspectionStandard(
        id="std-hard-001",
        item_id="BP-001",
        inspection_item_name="硬度",
        inspection_type="HARDNESS",
        lower_limit=80.0,
        upper_limit=95.0,
        unit="HRC",
    )
    db_session.add_all([std_dimension, std_hardness])

    # ロット
    from datetime import datetime

    lot = Lot(
        lot_number="20260401-BP-001",
        item_id="BP-001",
        line_code="LINE-BP",
        quantity=100,
        manufactured_at=datetime(2026, 4, 1, 8, 0, 0),
    )
    db_session.add(lot)
    db_session.commit()

    return {
        "item": item,
        "std_dimension": std_dimension,
        "std_hardness": std_hardness,
        "lot": lot,
    }


@pytest.fixture()
def service(db_session: Session) -> InspectionService:
    """InspectionService のインスタンスを生成する。"""
    return InspectionService(db_session)


# ---------- 正常系テスト ----------


class TestCreateInspectionSuccess:
    """検査結果登録の正常系テスト。"""

    def test_all_pass(
        self, service: InspectionService, sample_data: dict
    ) -> None:
        """全検査項目が合格の場合、全体結果も PASS になること。"""
        data = InspectionCreate(
            lot_number="20260401-BP-001",
            inspection_phase="IN_PROCESS",
            inspector_id="INS-001",
            details=[
                InspectionDetailCreate(
                    inspection_standard_id="std-dim-001",
                    measured_value=Decimal("12.25"),  # 範囲内
                ),
                InspectionDetailCreate(
                    inspection_standard_id="std-hard-001",
                    measured_value=Decimal("88.0"),  # 範囲内
                ),
            ],
        )

        result = service.create_inspection(data)

        assert result.result == "PASS"
        assert result.lot_number == "20260401-BP-001"
        assert result.inspection_phase == "IN_PROCESS"
        assert len(result.details) == 2
        assert all(d.judgment == "PASS" for d in result.details)

    def test_one_fail_makes_overall_fail(
        self, service: InspectionService, sample_data: dict
    ) -> None:
        """1項目でも不合格があれば、全体結果は FAIL になること。"""
        data = InspectionCreate(
            lot_number="20260401-BP-001",
            inspection_phase="IN_PROCESS",
            inspector_id="INS-001",
            details=[
                InspectionDetailCreate(
                    inspection_standard_id="std-dim-001",
                    measured_value=Decimal("12.25"),  # 範囲内（PASS）
                ),
                InspectionDetailCreate(
                    inspection_standard_id="std-hard-001",
                    measured_value=Decimal("96.0"),  # 上限超過（FAIL）
                ),
            ],
        )

        result = service.create_inspection(data)

        assert result.result == "FAIL"
        assert result.details[0].judgment == "PASS"
        assert result.details[1].judgment == "FAIL"


# ---------- 異常系テスト ----------


class TestCreateInspectionErrors:
    """検査結果登録の異常系テスト。"""

    def test_lot_not_found(
        self, service: InspectionService, sample_data: dict
    ) -> None:
        """存在しないロット番号を指定した場合、NotFoundException が発生すること。"""
        data = InspectionCreate(
            lot_number="99999999-XX-999",
            inspection_phase="IN_PROCESS",
            inspector_id="INS-001",
            details=[
                InspectionDetailCreate(
                    inspection_standard_id="std-dim-001",
                    measured_value=Decimal("12.25"),
                ),
            ],
        )

        with pytest.raises(NotFoundException) as exc_info:
            service.create_inspection(data)

        assert "99999999-XX-999" in exc_info.value.detail

    def test_duplicate_inspection(
        self, service: InspectionService, sample_data: dict
    ) -> None:
        """同一ロット・同一工程の検査が重複する場合、DuplicateException が発生すること。"""
        data = InspectionCreate(
            lot_number="20260401-BP-001",
            inspection_phase="FINAL",
            inspector_id="INS-001",
            details=[
                InspectionDetailCreate(
                    inspection_standard_id="std-dim-001",
                    measured_value=Decimal("12.25"),
                ),
            ],
        )

        # 1回目: 正常登録
        service.create_inspection(data)

        # 2回目: 重複エラー
        with pytest.raises(DuplicateException):
            service.create_inspection(data)

    def test_standard_not_found(
        self, service: InspectionService, sample_data: dict
    ) -> None:
        """存在しない検査基準IDを指定した場合、NotFoundException が発生すること。"""
        data = InspectionCreate(
            lot_number="20260401-BP-001",
            inspection_phase="INCOMING",
            inspector_id="INS-001",
            details=[
                InspectionDetailCreate(
                    inspection_standard_id="nonexistent-id",
                    measured_value=Decimal("12.25"),
                ),
            ],
        )

        with pytest.raises(NotFoundException) as exc_info:
            service.create_inspection(data)

        assert "nonexistent-id" in exc_info.value.detail


# ---------- 境界値テスト ----------


class TestJudgeBoundaryValues:
    """合否判定（_judge メソッド）の境界値テスト。

    検査基準: 下限値=12.00, 上限値=12.50 の場合
    """

    def test_exact_lower_limit_is_pass(self) -> None:
        """測定値が下限値と一致する場合、PASS となること。"""
        result = InspectionService._judge(
            Decimal("12.00"), Decimal("12.00"), Decimal("12.50")
        )
        assert result == "PASS"

    def test_exact_upper_limit_is_pass(self) -> None:
        """測定値が上限値と一致する場合、PASS となること。"""
        result = InspectionService._judge(
            Decimal("12.50"), Decimal("12.00"), Decimal("12.50")
        )
        assert result == "PASS"

    def test_just_below_lower_limit_is_fail(self) -> None:
        """測定値が下限値を 0.01 下回る場合、FAIL となること。"""
        result = InspectionService._judge(
            Decimal("11.99"), Decimal("12.00"), Decimal("12.50")
        )
        assert result == "FAIL"

    def test_just_above_upper_limit_is_fail(self) -> None:
        """測定値が上限値を 0.01 上回る場合、FAIL となること。"""
        result = InspectionService._judge(
            Decimal("12.51"), Decimal("12.00"), Decimal("12.50")
        )
        assert result == "FAIL"

    def test_middle_value_is_pass(self) -> None:
        """測定値が範囲の中央値の場合、PASS となること。"""
        result = InspectionService._judge(
            Decimal("12.25"), Decimal("12.00"), Decimal("12.50")
        )
        assert result == "PASS"

    def test_none_limits_is_pass(self) -> None:
        """上限値・下限値が None の場合（外観検査等）、PASS となること。"""
        result = InspectionService._judge(
            Decimal("1"), None, None
        )
        assert result == "PASS"
