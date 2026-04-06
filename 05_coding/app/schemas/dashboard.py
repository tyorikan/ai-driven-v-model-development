"""ダッシュボード関連の Pydantic スキーマ定義。"""

from datetime import datetime
from decimal import Decimal

from pydantic import BaseModel


class DefectRateResponse(BaseModel):
    """不良率集計のレスポンススキーマ。"""

    line_code: str
    period: str
    total_inspections: int
    failed_inspections: int
    defect_rate: Decimal


class QualityAlertResponse(BaseModel):
    """品質アラートのレスポンススキーマ。"""

    id: str
    line_code: str
    defect_rate: Decimal
    threshold: Decimal
    status: str
    triggered_at: datetime

    model_config = {"from_attributes": True}
