"""検査結果・検査明細の SQLAlchemy モデル定義。"""

from datetime import datetime
from uuid import uuid4

from sqlalchemy import DateTime, Integer, Numeric, String, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.item import Base


class InspectionResult(Base):
    """検査結果。1ロット1工程につき1レコード。"""

    __tablename__ = "inspection_result"

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: str(uuid4())
    )
    lot_number: Mapped[str] = mapped_column(
        String(20), ForeignKey("lot.lot_number"), nullable=False
    )
    inspection_phase: Mapped[str] = mapped_column(
        String(20), nullable=False
    )  # INCOMING, IN_PROCESS, FINAL, SHIPPING
    result: Mapped[str] = mapped_column(
        String(10), nullable=False
    )  # PASS, FAIL
    inspector_id: Mapped[str] = mapped_column(String(50), nullable=False)
    inspected_at: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, default=datetime.utcnow
    )
    revision: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    created_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow
    )

    lot: Mapped["Lot"] = relationship(back_populates="inspection_results")
    details: Mapped[list["InspectionDetail"]] = relationship(
        back_populates="inspection_result"
    )


class InspectionDetail(Base):
    """検査明細。検査項目ごとの測定値と判定。"""

    __tablename__ = "inspection_detail"

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: str(uuid4())
    )
    inspection_result_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("inspection_result.id"),
        nullable=False,
    )
    inspection_standard_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("inspection_standard.id"),
        nullable=False,
    )
    measured_value: Mapped[float] = mapped_column(
        Numeric(10, 2), nullable=False
    )
    judgment: Mapped[str] = mapped_column(
        String(10), nullable=False
    )  # PASS, FAIL

    inspection_result: Mapped["InspectionResult"] = relationship(
        back_populates="details"
    )


# 循環参照の解決
from app.models.lot import Lot  # noqa: E402, F401
