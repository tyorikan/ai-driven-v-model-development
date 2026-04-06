"""ロット関連の Pydantic スキーマ定義。"""

from datetime import datetime

from pydantic import BaseModel, Field


class LotCreate(BaseModel):
    """ロット登録のリクエストスキーマ（MES連携）。"""

    lot_number: str = Field(
        ...,
        pattern=r"^\d{8}-[A-Z]+-\d{3}$",
        description="ロット番号",
    )
    item_id: str = Field(..., description="品目コード")
    line_code: str = Field(..., description="ライン番号")
    quantity: int = Field(..., gt=0, description="製造数量")
    manufactured_at: datetime = Field(..., description="製造日時")


class LotResponse(BaseModel):
    """ロットのレスポンススキーマ。"""

    lot_number: str
    item_id: str
    line_code: str
    quantity: int
    manufactured_at: datetime
    source: str

    model_config = {"from_attributes": True}
