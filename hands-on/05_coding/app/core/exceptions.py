class AttendanceError(Exception):
    def __init__(self, detail: str):
        self.detail = detail
        super().__init__(detail)

class EmployeeNotFoundError(AttendanceError):
    error_code = "EMPLOYEE_NOT_FOUND"
    status_code = 404

class DuplicateClockInError(AttendanceError):
    error_code = "DUPLICATE_CLOCK_IN"
    status_code = 409

class ValidationError(AttendanceError):
    error_code = "VALIDATION_ERROR"
    status_code = 400
