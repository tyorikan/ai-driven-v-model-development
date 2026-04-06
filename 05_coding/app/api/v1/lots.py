"""ロット関連の API エンドポイント。"""

from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.exceptions import NotFoundException
from app.db.session import get_db
from app.models.lot import Lot
from app.schemas.lot import LotCreate, LotResponse

router = APIRouter(prefix="/api/v1/lots", tags=["lots"])


@router.post("", response_model=LotResponse, status_code=201)
def create_lot(
    data: LotCreate,
    db: Session = Depends(get_db),
) -> LotResponse:
    """ロットを登録する（MES連携用）。"""
    lot = Lot(
        lot_number=data.lot_number,
        item_id=data.item_id,
        line_code=data.line_code,
        quantity=data.quantity,
        manufactured_at=data.manufactured_at,
        source="MES",
    )
    db.add(lot)
    db.commit()
    db.refresh(lot)
    return LotResponse.model_validate(lot)


@router.get("/{lot_number}", response_model=LotResponse)
def get_lot(
    lot_number: str,
    db: Session = Depends(get_db),
) -> LotResponse:
    """ロットの詳細を取得する。"""
    lot = db.execute(
        select(Lot).where(Lot.lot_number == lot_number)
    ).scalar_one_or_none()
    if lot is None:
        raise NotFoundException("lot", lot_number)
    return LotResponse.model_validate(lot)
