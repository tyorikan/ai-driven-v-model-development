"""FastAPI アプリケーションのエントリーポイント。"""

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

from app.api.v1 import inspections, lots
from app.core.exceptions import AppException

app = FastAPI(
    title="製造ライン品質管理システム API",
    description="Manufacturing Quality Management System",
    version="1.0.0",
)

# ルーターの登録
app.include_router(inspections.router)
app.include_router(lots.router)


@app.exception_handler(AppException)
async def app_exception_handler(
    request: Request, exc: AppException
) -> JSONResponse:
    """アプリケーション例外のハンドラ。"""
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "error_code": exc.error_code,
            "detail": exc.detail,
        },
    )
