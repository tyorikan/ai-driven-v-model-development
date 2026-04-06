"""アプリケーション設定管理。"""

from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """環境変数から読み込むアプリケーション設定。"""

    database_url: str = "postgresql://user:password@localhost:5432/quality_db"
    alert_threshold_percent: float = 3.0
    alert_check_window_hours: int = 1
    smtp_host: str = "localhost"
    smtp_port: int = 587

    model_config = {"env_prefix": "QMS_"}


settings = Settings()
