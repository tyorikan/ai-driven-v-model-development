"""検査業務のビジネスロジック。"""

from datetime import datetime
from decimal import Decimal
from uuid import uuid4

from sqlalchemy.orm import Session, joinedload
from sqlalchemy import select

from app.core.exceptions import NotFoundException, DuplicateException
from app.models.inspection import InspectionResult, InspectionDetail
from app.models.item import InspectionStandard
from app.models.lot import Lot
from app.schemas.inspection import (
    InspectionCreate,
    InspectionDetailResponse,
    InspectionResponse,
)


class InspectionService:
    """検査結果の登録・取得を行うサービスクラス。"""

    def __init__(self, db: Session) -> None:
        self.db = db

    def create_inspection(self, data: InspectionCreate) -> InspectionResponse:
        """検査結果を登録し、合否を自動判定する。

        Args:
            data: 検査結果登録リクエスト

        Returns:
            登録された検査結果（合否判定結果を含む）

        Raises:
            NotFoundException: ロットまたは検査基準が存在しない場合
            DuplicateException: 同一ロット・同一工程の検査が既に存在する場合
        """
        # 1. ロットの存在チェック
        lot = self.db.execute(
            select(Lot).where(Lot.lot_number == data.lot_number)
        ).scalar_one_or_none()
        if lot is None:
            raise NotFoundException("lot", data.lot_number)

        # 2. 重複チェック
        existing = self.db.execute(
            select(InspectionResult).where(
                InspectionResult.lot_number == data.lot_number,
                InspectionResult.inspection_phase == data.inspection_phase,
            )
        ).scalar_one_or_none()
        if existing is not None:
            raise DuplicateException(
                f"ロット '{data.lot_number}' の工程 '{data.inspection_phase}' "
                f"は既に検査済みです"
            )

        # 3. 検査基準の取得と合否判定
        detail_responses: list[InspectionDetailResponse] = []
        detail_models: list[InspectionDetail] = []
        overall_result = "PASS"

        for detail in data.details:
            standard = self.db.execute(
                select(InspectionStandard).where(
                    InspectionStandard.id == detail.inspection_standard_id
                )
            ).scalar_one_or_none()
            if standard is None:
                raise NotFoundException(
                    "inspection_standard", detail.inspection_standard_id
                )

            # 合否判定: 下限値 <= 測定値 <= 上限値
            judgment = self._judge(
                detail.measured_value,
                Decimal(str(standard.lower_limit)) if standard.lower_limit else None,
                Decimal(str(standard.upper_limit)) if standard.upper_limit else None,
            )
            if judgment == "FAIL":
                overall_result = "FAIL"

            detail_model = InspectionDetail(
                id=str(uuid4()),
                inspection_standard_id=detail.inspection_standard_id,
                measured_value=float(detail.measured_value),
                judgment=judgment,
            )
            detail_models.append(detail_model)

            detail_responses.append(
                InspectionDetailResponse(
                    inspection_item_name=standard.inspection_item_name,
                    measured_value=detail.measured_value,
                    lower_limit=Decimal(str(standard.lower_limit or 0)),
                    upper_limit=Decimal(str(standard.upper_limit or 0)),
                    unit=standard.unit,
                    judgment=judgment,
                )
            )

        # 4. 検査結果の保存
        now = datetime.utcnow()
        result = InspectionResult(
            id=str(uuid4()),
            lot_number=data.lot_number,
            inspection_phase=data.inspection_phase,
            result=overall_result,
            inspector_id=data.inspector_id,
            inspected_at=now,
        )
        for dm in detail_models:
            dm.inspection_result_id = result.id

        self.db.add(result)
        self.db.add_all(detail_models)
        self.db.commit()

        return InspectionResponse(
            id=result.id,
            lot_number=result.lot_number,
            inspection_phase=result.inspection_phase,
            result=overall_result,
            inspector_id=result.inspector_id,
            inspected_at=now,
            details=detail_responses,
        )

    def get_inspections(
        self,
        lot_number: str | None = None,
        inspection_phase: str | None = None,
        limit: int = 50,
        offset: int = 0,
    ) -> list[InspectionResponse]:
        """検査結果を条件指定で取得する。

        Args:
            lot_number: ロット番号（フィルタ）
            inspection_phase: 検査工程（フィルタ）
            limit: 取得件数上限
            offset: オフセット

        Returns:
            検査結果のリスト
        """
        query = select(InspectionResult).options(
            joinedload(InspectionResult.details)
        )
        if lot_number:
            query = query.where(InspectionResult.lot_number == lot_number)
        if inspection_phase:
            query = query.where(
                InspectionResult.inspection_phase == inspection_phase
            )
        query = query.order_by(InspectionResult.inspected_at.desc())
        query = query.limit(limit).offset(offset)

        results = self.db.execute(query).unique().scalars().all()
        return [self._to_response(r) for r in results]

    @staticmethod
    def _judge(
        measured: Decimal,
        lower: Decimal | None,
        upper: Decimal | None,
    ) -> str:
        """測定値が基準範囲内かどうかを判定する。

        Args:
            measured: 測定値
            lower: 下限値（None の場合はチェックしない）
            upper: 上限値（None の場合はチェックしない）

        Returns:
            "PASS" または "FAIL"
        """
        if lower is not None and measured < lower:
            return "FAIL"
        if upper is not None and measured > upper:
            return "FAIL"
        return "PASS"

    def _to_response(self, result: InspectionResult) -> InspectionResponse:
        """DB モデルをレスポンススキーマに変換する。"""
        detail_responses = []
        for d in result.details:
            standard = self.db.execute(
                select(InspectionStandard).where(
                    InspectionStandard.id == d.inspection_standard_id
                )
            ).scalar_one()
            detail_responses.append(
                InspectionDetailResponse(
                    inspection_item_name=standard.inspection_item_name,
                    measured_value=Decimal(str(d.measured_value)),
                    lower_limit=Decimal(str(standard.lower_limit or 0)),
                    upper_limit=Decimal(str(standard.upper_limit or 0)),
                    unit=standard.unit,
                    judgment=d.judgment,
                )
            )
        return InspectionResponse(
            id=result.id,
            lot_number=result.lot_number,
            inspection_phase=result.inspection_phase,
            result=result.result,
            inspector_id=result.inspector_id,
            inspected_at=result.inspected_at,
            details=detail_responses,
        )
