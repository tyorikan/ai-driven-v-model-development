"""検査関連の API エンドポイント。"""

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.schemas.inspection import InspectionCreate, InspectionResponse
from app.services.alert_service import AlertService
from app.services.inspection_service import InspectionService

router = APIRouter(prefix="/api/v1/inspections", tags=["inspections"])


@router.post("", response_model=InspectionResponse, status_code=201)
def create_inspection(
    data: InspectionCreate,
    db: Session = Depends(get_db),
) -> InspectionResponse:
    """検査結果を登録する。

    測定値を基に合否を自動判定し、不合格の場合は
    品質アラートの判定を実行する。
    """
    service = InspectionService(db)
    result = service.create_inspection(data)

    # 不合格の場合、アラート判定を実行
    if result.result == "FAIL":
        from app.models.lot import Lot
        from sqlalchemy import select

        lot = db.execute(
            select(Lot).where(Lot.lot_number == data.lot_number)
        ).scalar_one()
        alert_service = AlertService(db)
        alert_service.check_and_trigger_alert(lot.line_code)

    return result


@router.get("", response_model=list[InspectionResponse])
def list_inspections(
    lot_number: str | None = Query(None, description="ロット番号"),
    inspection_phase: str | None = Query(None, description="検査工程"),
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    db: Session = Depends(get_db),
) -> list[InspectionResponse]:
    """検査結果の一覧を取得する。"""
    service = InspectionService(db)
    return service.get_inspections(
        lot_number=lot_number,
        inspection_phase=inspection_phase,
        limit=limit,
        offset=offset,
    )
