"""ロットの SQLAlchemy モデル定義。"""

from datetime import datetime

from sqlalchemy import DateTime, Integer, String, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.item import Base


class Lot(Base):
    """製造ロット。MES から連携されるデータ。"""

    __tablename__ = "lot"

    lot_number: Mapped[str] = mapped_column(String(20), primary_key=True)
    item_id: Mapped[str] = mapped_column(
        String(50), ForeignKey("item.item_id"), nullable=False
    )
    line_code: Mapped[str] = mapped_column(String(20), nullable=False)
    quantity: Mapped[int] = mapped_column(Integer, nullable=False)
    manufactured_at: Mapped[datetime] = mapped_column(
        DateTime, nullable=False
    )
    source: Mapped[str] = mapped_column(
        String(10), nullable=False, default="MES"
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow
    )

    inspection_results: Mapped[list["InspectionResult"]] = relationship(
        back_populates="lot"
    )


# 循環参照を避けるため、InspectionResult は inspection.py で定義
from app.models.inspection import InspectionResult  # noqa: E402, F401
