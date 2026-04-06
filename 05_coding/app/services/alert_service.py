"""品質アラートのビジネスロジック。"""

import logging
from datetime import datetime, timedelta
from uuid import uuid4

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core.config import settings
from app.models.defect import QualityAlert
from app.models.inspection import InspectionResult

logger = logging.getLogger(__name__)


class AlertService:
    """品質アラートの判定・発行を行うサービスクラス。"""

    def __init__(self, db: Session) -> None:
        self.db = db

    def check_and_trigger_alert(self, line_code: str) -> QualityAlert | None:
        """直近1時間の不良率をチェックし、閾値超過時にアラートを発行する。

        Args:
            line_code: チェック対象のライン番号

        Returns:
            アラートを発行した場合は QualityAlert、それ以外は None
        """
        window_start = datetime.utcnow() - timedelta(
            hours=settings.alert_check_window_hours
        )

        # 直近1時間の検査件数を集計
        stats = self.db.execute(
            select(
                func.count(InspectionResult.id).label("total"),
                func.count(
                    func.nullif(InspectionResult.result, "PASS")
                ).label("failed"),
            )
            .join(
                # ロットからライン番号を取得するために結合
                InspectionResult.lot
            )
            .where(
                InspectionResult.inspected_at >= window_start,
                InspectionResult.lot.has(line_code=line_code),
            )
        ).one()

        total = stats.total
        failed = stats.failed

        if total == 0:
            return None

        defect_rate = (failed / total) * 100

        if defect_rate <= settings.alert_threshold_percent:
            return None

        # アラートを発行
        alert = QualityAlert(
            id=str(uuid4()),
            line_code=line_code,
            defect_rate=round(defect_rate, 2),
            threshold=settings.alert_threshold_percent,
            status="OPEN",
        )
        self.db.add(alert)
        self.db.commit()

        logger.warning(
            "品質アラート発行: ライン=%s, 不良率=%.2f%%, 閾値=%.2f%%",
            line_code,
            defect_rate,
            settings.alert_threshold_percent,
        )

        return alert
