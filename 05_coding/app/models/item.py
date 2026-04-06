"""品目・検査基準の SQLAlchemy モデル定義。"""

from datetime import datetime
from uuid import uuid4

from sqlalchemy import Boolean, DateTime, Numeric, String, ForeignKey
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


class Base(DeclarativeBase):
    """SQLAlchemy モデルの基底クラス。"""
    pass


class Item(Base):
    """品目マスタ。"""

    __tablename__ = "item"

    item_id: Mapped[str] = mapped_column(String(50), primary_key=True)
    item_name: Mapped[str] = mapped_column(String(200), nullable=False)
    category: Mapped[str] = mapped_column(String(50), nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, onupdate=datetime.utcnow
    )

    standards: Mapped[list["InspectionStandard"]] = relationship(
        back_populates="item"
    )


class InspectionStandard(Base):
    """検査基準マスタ。"""

    __tablename__ = "inspection_standard"

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: str(uuid4())
    )
    item_id: Mapped[str] = mapped_column(
        String(50), ForeignKey("item.item_id"), nullable=False
    )
    inspection_item_name: Mapped[str] = mapped_column(
        String(100), nullable=False
    )
    inspection_type: Mapped[str] = mapped_column(
        String(30), nullable=False
    )  # DIMENSION, HARDNESS, APPEARANCE, ROUGHNESS
    lower_limit: Mapped[float | None] = mapped_column(Numeric(10, 2))
    upper_limit: Mapped[float | None] = mapped_column(Numeric(10, 2))
    unit: Mapped[str] = mapped_column(String(20), nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)

    item: Mapped["Item"] = relationship(back_populates="standards")
