"""InspectionService の単体テスト（TDD: このファイルを最初に作成）。

テスト対象: app/services/inspection_service.py
対応する設計書: 04_detailed_design/detailed_design.md セクション 3.1

TDD の手順:
1. [Red] このテストファイルを先に作成し、テスト実行 → 全て FAIL を確認
2. [Green] 実装コード（inspection_service.py 等）を作成し、テスト実行 → 全て PASS
3. [Refactor] 実装コードをリファクタリングし、テスト実行 → 全て PASS を維持
"""

from datetime import datetime
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
    """テスト用のインメモリ SQLite セッションを生成する。

    各テストごとに新しい DB を作成し、テスト終了後にクローズする。
    """
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    session = sessionmaker(bind=engine)()
    yield session
    session.close()


@pytest.fixture()
def sample_data(db_session: Session) -> dict:
    """テスト用のマスタデータとロットを投入する。

    投入データ:
    - 品目: BP-001（ブレーキパッド Type-A）
    - 検査基準: 外径寸法（12.00〜12.50mm）, 硬度（80〜95 HRC）
    - ロット: 20260401-BP-001（LINE-BP, 数量100）
    """
    item = Item(
        item_id="BP-001",
        item_name="ブレーキパッド Type-A",
        category="ブレーキパッド",
    )
    db_session.add(item)

    std_dimension = InspectionStandard(
        id="std-dim-001",
        item_id="BP-001",
        inspection_item_name="外径寸法",
        inspection_type="DIMENSION",
        lower_limit=12.00,
        upper_limit=12.50,
        unit="mm",
    )
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
    """検査結果登録の正常系テスト。

    詳細設計書 セクション 3.1 InspectionService.create_inspection() の
    正常系処理フローを検証する。
    """

    def test_all_pass(
        self, service: InspectionService, sample_data: dict
    ) -> None:
        """全検査項目が合格の場合、全体結果も PASS になること。

        入力: 外径寸法=12.25（範囲: 12.00〜12.50）, 硬度=88.0（範囲: 80〜95）
        期待: result="PASS", 全 detail の judgment="PASS"
        """
        data = InspectionCreate(
            lot_number="20260401-BP-001",
            inspection_phase="IN_PROCESS",
            inspector_id="INS-001",
            details=[
                InspectionDetailCreate(
                    inspection_standard_id="std-dim-001",
                    measured_value=Decimal("12.25"),
                ),
                InspectionDetailCreate(
                    inspection_standard_id="std-hard-001",
                    measured_value=Decimal("88.0"),
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
        """1項目でも不合格があれば、全体結果は FAIL になること。

        入力: 外径寸法=12.25（PASS）, 硬度=96.0（上限 95.0 を超過 → FAIL）
        期待: result="FAIL", 外径寸法=PASS, 硬度=FAIL
        """
        data = InspectionCreate(
            lot_number="20260401-BP-001",
            inspection_phase="IN_PROCESS",
            inspector_id="INS-001",
            details=[
                InspectionDetailCreate(
                    inspection_standard_id="std-dim-001",
                    measured_value=Decimal("12.25"),
                ),
                InspectionDetailCreate(
                    inspection_standard_id="std-hard-001",
                    measured_value=Decimal("96.0"),
                ),
            ],
        )

        result = service.create_inspection(data)

        assert result.result == "FAIL"
        assert result.details[0].judgment == "PASS"
        assert result.details[1].judgment == "FAIL"


# ---------- 異常系テスト ----------


class TestCreateInspectionErrors:
    """検査結果登録の異常系テスト。

    詳細設計書 セクション 5 エラーハンドリング設計のエラーコードを検証する。
    """

    def test_lot_not_found(
        self, service: InspectionService, sample_data: dict
    ) -> None:
        """存在しないロット番号を指定した場合、NotFoundException が発生すること。

        入力: lot_number="99999999-XX-999"（存在しない）
        期待: NotFoundException, detail に "99999999-XX-999" を含む
        """
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
        """同一ロット・同一工程の検査が重複する場合、DuplicateException が発生すること。

        入力: 同一ロット（20260401-BP-001）・同一工程（FINAL）で 2 回登録
        期待: 1 回目は成功、2 回目で DuplicateException
        """
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
        """存在しない検査基準IDを指定した場合、NotFoundException が発生すること。

        入力: inspection_standard_id="nonexistent-id"（存在しない）
        期待: NotFoundException, detail に "nonexistent-id" を含む
        """
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

    検査基準: lower_limit=12.00, upper_limit=12.50 の場合について、
    境界値分析に基づきテストする。

    境界値のテストパターン:
    - ON（境界値ちょうど）: 12.00, 12.50 → PASS
    - OFF（境界値の外側）: 11.99, 12.51 → FAIL
    - IN（範囲内の代表値）: 12.25 → PASS
    """

    def test_exact_lower_limit_is_pass(self) -> None:
        """測定値が下限値と一致する場合（12.00）、PASS となること。"""
        result = InspectionService._judge(
            Decimal("12.00"), Decimal("12.00"), Decimal("12.50")
        )
        assert result == "PASS"

    def test_exact_upper_limit_is_pass(self) -> None:
        """測定値が上限値と一致する場合（12.50）、PASS となること。"""
        result = InspectionService._judge(
            Decimal("12.50"), Decimal("12.00"), Decimal("12.50")
        )
        assert result == "PASS"

    def test_just_below_lower_limit_is_fail(self) -> None:
        """測定値が下限値を 0.01 下回る場合（11.99）、FAIL となること。"""
        result = InspectionService._judge(
            Decimal("11.99"), Decimal("12.00"), Decimal("12.50")
        )
        assert result == "FAIL"

    def test_just_above_upper_limit_is_fail(self) -> None:
        """測定値が上限値を 0.01 上回る場合（12.51）、FAIL となること。"""
        result = InspectionService._judge(
            Decimal("12.51"), Decimal("12.00"), Decimal("12.50")
        )
        assert result == "FAIL"

    def test_middle_value_is_pass(self) -> None:
        """測定値が範囲の中央値（12.25）の場合、PASS となること。"""
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
