from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from app.api.v1.attendance import router as attendance_router
from app.core.exceptions import AttendanceError

app = FastAPI(title="Attendance Management System", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.exception_handler(AttendanceError)
async def attendance_exception_handler(request: Request, exc: AttendanceError):
    return JSONResponse(
        status_code=getattr(exc, "status_code", 400),
        content={
            "error_code": getattr(exc, "error_code", "UNKNOWN_ERROR"),
            "detail": exc.detail
        },
    )

app.include_router(attendance_router)
