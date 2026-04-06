"""カスタム例外クラス定義。"""


class AppException(Exception):
    """アプリケーション共通の基底例外。"""

    def __init__(
        self, error_code: str, detail: str, status_code: int = 400
    ) -> None:
        self.error_code = error_code
        self.detail = detail
        self.status_code = status_code
        super().__init__(detail)


class NotFoundException(AppException):
    """リソースが見つからない場合の例外。"""

    def __init__(self, resource: str, identifier: str) -> None:
        super().__init__(
            error_code=f"{resource.upper()}_NOT_FOUND",
            detail=f"{resource} '{identifier}' は存在しません",
            status_code=404,
        )


class DuplicateException(AppException):
    """リソースが重複する場合の例外。"""

    def __init__(self, detail: str) -> None:
        super().__init__(
            error_code="DUPLICATE_INSPECTION",
            detail=detail,
            status_code=409,
        )
