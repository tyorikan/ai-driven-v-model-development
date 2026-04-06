from enum import Enum

class RoleEnum(str, Enum):
    GENERAL = "一般"
    MANAGER = "管理職"
    HR = "総務"
    ADMIN = "管理者"

class EmploymentTypeEnum(str, Enum):
    REGULAR = "正社員"
    CONTRACT = "契約社員"
    PART_TIME = "パート"

class RecordTypeEnum(str, Enum):
    CLOCK_IN = "出勤"
    CLOCK_OUT = "退勤"
