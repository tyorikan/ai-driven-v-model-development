"""不良記録・品質アラート・出荷判定の SQLAlchemy モデル定義。"""

from datetime import datetime
from uuid import uuid4

from sqlalchemy import DateTime, Numeric, String, Text, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column

from app.models.item import Base


class DefectRecord(Base):
    """不良記録。不合格の検査結果に紐づく。"""

    __tablename__ = "defect_record"

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: str(uuid4())
    )
    inspection_result_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("inspection_result.id"),
        nullable=False,
    )
    defect_category: Mapped[str] = mapped_column(
        String(30), nullable=False
    )  # DIMENSION, APPEARANCE, MATERIAL, OTHER
    defect_description: Mapped[str] = mapped_column(Text, nullable=False)
    disposition: Mapped[str] = mapped_column(
        String(20), nullable=False
    )  # SCRAP, REWORK, USE_AS_IS
    created_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow
    )


class QualityAlert(Base):
    """品質アラート。不良率が閾値を超えた場合に生成。"""

    __tablename__ = "quality_alert"

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: str(uuid4())
    )
    line_code: Mapped[str] = mapped_column(String(20), nullable=False)
    defect_rate: Mapped[float] = mapped_column(
        Numeric(5, 2), nullable=False
    )
    threshold: Mapped[float] = mapped_column(Numeric(5, 2), nullable=False)
    status: Mapped[str] = mapped_column(
        String(10), nullable=False, default="OPEN"
    )  # OPEN, CLOSED
    triggered_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow
    )


class ShipmentDecision(Base):
    """出荷判定。ロット単位の出荷可否判定。"""

    __tablename__ = "shipment_decision"

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: str(uuid4())
    )
    lot_number: Mapped[str] = mapped_column(
        String(20), ForeignKey("lot.lot_number"), nullable=False
    )
    decision: Mapped[str] = mapped_column(
        String(10), nullable=False
    )  # SHIP, HOLD
    decided_by: Mapped[str] = mapped_column(String(50), nullable=False)
    reason: Mapped[str | None] = mapped_column(Text)
    decided_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow
    )
