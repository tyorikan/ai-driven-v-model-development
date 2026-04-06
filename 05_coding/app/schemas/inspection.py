"""検査関連の Pydantic スキーマ定義。"""

from datetime import datetime
from decimal import Decimal

from pydantic import BaseModel, Field


class InspectionDetailCreate(BaseModel):
    """検査明細の入力スキーマ。"""

    inspection_standard_id: str = Field(
        ..., description="検査基準ID"
    )
    measured_value: Decimal = Field(
        ..., description="測定値"
    )


class InspectionCreate(BaseModel):
    """検査結果登録のリクエストスキーマ。"""

    lot_number: str = Field(
        ...,
        pattern=r"^\d{8}-[A-Z]+-\d{3}$",
        description="ロット番号（例: 20260401-BP-001）",
    )
    inspection_phase: str = Field(
        ...,
        pattern=r"^(INCOMING|IN_PROCESS|FINAL|SHIPPING)$",
        description="検査工程",
    )
    inspector_id: str = Field(
        ..., min_length=1, max_length=50, description="検査員ID"
    )
    details: list[InspectionDetailCreate] = Field(
        ..., min_length=1, description="検査明細（1件以上必須）"
    )


class InspectionDetailResponse(BaseModel):
    """検査明細のレスポンススキーマ。"""

    inspection_item_name: str
    measured_value: Decimal
    lower_limit: Decimal
    upper_limit: Decimal
    unit: str
    judgment: str

    model_config = {"from_attributes": True}


class InspectionResponse(BaseModel):
    """検査結果のレスポンススキーマ。"""

    id: str
    lot_number: str
    inspection_phase: str
    result: str
    inspector_id: str
    inspected_at: datetime
    details: list[InspectionDetailResponse]

    model_config = {"from_attributes": True}
