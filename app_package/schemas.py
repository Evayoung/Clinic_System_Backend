from datetime import datetime, date, time
from enum import Enum
from typing import Optional, List
from pydantic import BaseModel, EmailStr, validator
import re

# Enums (aligned with models.py)
class UserStatus(str, Enum):
    active = "active"
    inactive = "inactive"

class UserRole(str, Enum):
    doctor = "doctor"
    admin = "admin"
    pharmacist = "pharmacist"
    lab_attendant = "lab_attendant"

class StudentStatus(str, Enum):
    active = "active"
    inactive = "inactive"

class BloodGroup(str, Enum):
    A_positive = "A+"
    A_negative = "A-"
    B_positive = "B+"
    B_negative = "B-"
    AB_positive = "AB+"
    AB_negative = "AB-"
    O_positive = "O+"
    O_negative = "O-"

class Genotype(str, Enum):
    AA = "AA"
    AS = "AS"
    SS = "SS"
    AC = "AC"
    SC = "SC"

class CardStatus(str, Enum):
    active = "active"
    inactive = "inactive"

class VisitStatus(str, Enum):
    pending = "pending"
    completed = "completed"
    cancelled = "cancelled"

class AppointmentStatus(str, Enum):
    available = "available"
    booked = "booked"
    completed = "completed"
    cancelled = "cancelled"
    pending = "pending"

class AvailabilityStatus(str, Enum):
    active = "active"
    inactive = "inactive"

class DayOfWeek(str, Enum):
    Monday = "Monday"
    Tuesday = "Tuesday"
    Wednesday = "Wednesday"
    Thursday = "Thursday"
    Friday = "Friday"
    Saturday = "Saturday"
    Sunday = "Sunday"

class Gender(str, Enum):
    male = "male"
    female = "female"
    other = "other"

class FacultyType(str, Enum):
    Art = "Arts"
    Engineering = "Engineering"
    Medical = "Medical"
    Education = "Education"
    Sciences = "Sciences"

# ----------------------------------- Authentication Schemas -----------------------------------
class Token(BaseModel):
    access_token: str
    token_type: str

    class Config:
        from_attributes = True

class TokenData(BaseModel):
    user_id: Optional[str] = None
    student_id: Optional[int] = None
    role: Optional[str] = None

    class Config:
        from_attributes = True

class UserLogin(BaseModel):
    user_id: str
    password: str

    @validator("user_id")
    def validate_user_id(cls, v):
        if not re.match(r"^UIL/\d{2}/\d{3}$", v):
            raise ValueError("Invalid user_id format (e.g., UIL/23/123)")
        return v

    class Config:
        from_attributes = True

class UserLoginResponse(BaseModel):
    access_token: str
    token_type: str
    username: str
    user_id: str
    email: EmailStr
    phone: Optional[str]
    role: UserRole

    class Config:
        from_attributes = True

class StudentLogin(BaseModel):
    matriculation_number: str
    password: str

    # @validator("matriculation_number")
    # def validate_matric_number(cls, v):
    #     if not re.match(r"^UIL/\d{2}/\d{6}$", v):
    #         raise ValueError("Invalid matriculation number format (e.g., UIL/23/123456)")
    #     return v

    class Config:
        from_attributes = True

class StudentLoginResponse(BaseModel):
    access_token: str
    token_type: str
    student_id: int
    matriculation_number: str
    first_name: str
    surname: str
    email: EmailStr
    profile_picture: str
    faculty_name: str
    department_name: str

    class Config:
        from_attributes = True

class PasswordReset(BaseModel):
    user_id: Optional[str] = None
    student_id: Optional[str] = None
    new_password: str

    # @validator("new_password")
    # def validate_password(cls, v):
    #     if len(v) < 8:
    #         raise ValueError("Password must be at least 8 characters long")
    #     return v

    class Config:
        from_attributes = True

# ----------------------------------- User Schemas -----------------------------------
class UserCreate(BaseModel):
    username: str
    password: str
    role: UserRole
    email: EmailStr
    phone: Optional[str] = None
    status: Optional[UserStatus] = UserStatus.active

    class Config:
        from_attributes = True

class CreateAdmin(BaseModel):
    """ *** Schemas used to create the admin details *** """
    username: str
    password: str
    email: EmailStr
    phone: Optional[str] = None
    status: Optional[UserStatus] = UserStatus.active

    class Config:
        from_attributes = True


class UserUpdate(BaseModel):
    username: Optional[str] = None
    password: Optional[str] = None
    role: Optional[UserRole] = None
    email: Optional[EmailStr] = None
    phone: Optional[str] = None
    status: Optional[UserStatus] = None

    class Config:
        from_attributes = True


class UserResponse(BaseModel):
    user_id: str
    username: str
    role: UserRole
    email: EmailStr
    phone: Optional[str]
    status: UserStatus
    created_at: datetime
    updated_at: Optional[datetime]
    last_login: Optional[datetime]

    class Config:
        from_attributes = True

# ----------------------------------- Student Schemas -----------------------------------
class StudentCreate(BaseModel):
    matriculation_number: str
    first_name: str
    surname: str
    email: EmailStr
    session_id: int
    phone: str
    date_of_birth: date
    gender: Gender
    address: Optional[str] = None
    role: str = "student"
    password: str
    faculty_id: int
    department_id: int
    level_id: int
    emergency_contact: Optional[str] = None
    profile_picture: Optional[str] = None
    status: Optional[StudentStatus] = StudentStatus.active

    # @validator("matriculation_number")
    # def validate_matric_number(cls, v):
    #     if not re.match(r"^\d{2}/\s{2}/\d{3}$", v):
    #         raise ValueError("Invalid matriculation number format (e.g., 15/56EG123)")
    #     return v

    class Config:
        from_attributes = True

class StudentUpdate(BaseModel):
    first_name: Optional[str] = None
    surname: Optional[str] = None
    email: Optional[EmailStr] = None
    session_id: Optional[str] = None
    phone: Optional[str] = None
    date_of_birth: Optional[date] = None
    gender: Optional[Gender] = None
    address: Optional[str] = None
    password: Optional[str] = None
    faculty_id: Optional[str] = None
    department_id: Optional[str] = None
    level_id: Optional[str] = None
    emergency_contact: Optional[str] = None
    profile_picture: Optional[str] = None
    status: Optional[StudentStatus] = None

    class Config:
        from_attributes = True

class StudentResponse(BaseModel):
    student_id: int
    matriculation_number: str
    first_name: str
    surname: str
    email: EmailStr
    session_id: int
    phone: str
    date_of_birth: date
    gender: Gender
    address: Optional[str]
    role: str
    faculty_id: int
    department_id: int
    level_id: int
    emergency_contact: Optional[str]
    profile_picture: Optional[str]
    status: StudentStatus
    created_at: datetime
    updated_at: Optional[datetime]
    last_login: Optional[datetime]

    class Config:
        from_attributes = True

class StudentWithRelationsResponse(BaseModel):
    student_id: int
    matriculation_number: str
    first_name: str
    surname: str
    email: EmailStr
    session_name: str  # Instead of session_id
    phone: str
    date_of_birth: date
    gender: Gender
    address: Optional[str]
    role: str
    faculty_name: str  # Instead of faculty_id
    department_name: str  # Instead of department_id
    level_name: str  # Instead of level_id
    emergency_contact: Optional[str]
    profile_picture: Optional[str]
    status: StudentStatus
    created_at: datetime
    updated_at: Optional[datetime]
    last_login: Optional[datetime]

    class Config:
        from_attributes = True

# ----------------------------------- Clinic Card Schemas -----------------------------------
class ClinicCardCreate(BaseModel):
    student_id: int
    clinic_number: str
    issue_date: date
    expiry_date: Optional[date] = None
    status: Optional[CardStatus] = CardStatus.active

    class Config:
        from_attributes = True

class ClinicCardResponse(BaseModel):
    card_id: int
    student_id: int
    clinic_number: str
    issue_date: date
    expiry_date: Optional[date]
    status: CardStatus
    qr_code: Optional[str]  # Base64-encoded QR code image
    created_at: datetime
    updated_at: Optional[datetime]

    class Config:
        from_attributes = True

# ----------------------------------- Health Record Schemas -----------------------------------
class HealthRecordCreate(BaseModel):
    matric_number: str  # Changed from student_id to matric_number
    blood_group: Optional[BloodGroup] = None
    genotype: Optional[Genotype] = None
    height: Optional[float] = None
    weight: Optional[float] = None
    test_date: date
    notes: Optional[str] = None

    class Config:
        from_attributes = True

class HealthRecordResponse1(BaseModel):
    health_record_id: int
    student_id: int
    blood_group: Optional[BloodGroup]
    genotype: Optional[Genotype]
    height: Optional[float]
    weight: Optional[float]
    test_date: date
    lab_attendant_id: str
    notes: Optional[str]
    created_at: datetime
    updated_at: Optional[datetime]

    class Config:
        from_attributes = True


class HealthRecordResponse(BaseModel):
    student_name: str
    matric_number: str
    department: str
    blood_group: Optional[BloodGroup]
    genotype: Optional[Genotype]
    height: Optional[float]
    weight: Optional[float]
    test_date: date
    notes: Optional[str]
    created_at: datetime
    updated_at: Optional[datetime]

    class Config:
        from_attributes = True


class HealthRecordUpdate(BaseModel):
    blood_group: Optional[BloodGroup] = None
    genotype: Optional[Genotype] = None
    height: Optional[float] = None
    weight: Optional[float] = None
    test_date: Optional[date] = None
    notes: Optional[str] = None

    class Config:
        from_attributes = True

# ----------------------------------- Clinic Visit Schemas -----------------------------------
class ClinicVisitCreate(BaseModel):
    student_id: int
    schedule_id: Optional[int] = None
    visit_date: date
    status: Optional[VisitStatus] = VisitStatus.pending

    class Config:
        from_attributes = True

class ClinicVisitResponse(BaseModel):
    visit_id: int
    student_id: int
    doctor_id: str
    schedule_id: Optional[int]
    visit_date: date
    status: VisitStatus
    created_at: datetime

    class Config:
        from_attributes = True

# ----------------------------------- Complaint Schemas -----------------------------------
"""class ComplaintCreate(BaseModel):
    visit_id: int
    student_id: int
    complaint_description: str

    class Config:
        from_attributes = True"""


class ComplaintCreate(BaseModel):
    schedule_id: int
    complaint_description: str


class ComplaintResponse(BaseModel):
    complaint_id: int
    visit_id: int
    student_id: int
    doctor_id: str
    complaint_description: str
    created_at: datetime

    class Config:
        from_attributes = True

# ----------------------------------- Diagnosis Schemas -----------------------------------
class DiagnosisCreate(BaseModel):
    visit_id: int
    complaint_id: int
    student_id: int
    diagnosis_description: str
    treatment_plan: Optional[str] = None

    class Config:
        from_attributes = True

class DiagnosisResponse(BaseModel):
    diagnosis_id: int
    visit_id: int
    student_id: int
    doctor_id: str
    diagnosis_description: str
    treatment_plan: Optional[str]
    created_at: datetime

    class Config:
        from_attributes = True

# ----------------------------------- Prescription Schemas -----------------------------------
class PrescriptionCreate(BaseModel):
    diagnosis_id: int
    student_id: int
    drug_id: int
    dosage: str
    instructions: Optional[str] = None

    class Config:
        from_attributes = True

class PrescriptionResponse(BaseModel):
    prescription_id: int
    diagnosis_id: int
    student_id: int
    doctor_id: str
    drug_id: int
    dosage: str
    instructions: Optional[str]
    created_at: datetime

    class Config:
        from_attributes = True

# ----------------------------------- Drug Dispensation Schemas -----------------------------------
class DrugDispensationCreate(BaseModel):
    prescription_id: int
    student_id: int
    drug_id: int
    quantity: int
    dispense_date: date

    class Config:
        from_attributes = True

class DrugDispensationResponse(BaseModel):
    dispensation_id: int
    prescription_id: int
    student_id: int
    pharmacist_id: str
    drug_id: int
    quantity: int
    dispense_date: date
    created_at: datetime

    class Config:
        from_attributes = True

# ----------------------------------- Drug Schemas -----------------------------------
class DrugCreate(BaseModel):
    name: str
    description: Optional[str] = None
    stock_level: Optional[int] = None

    class Config:
        from_attributes = True

class DrugUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    stock_level: Optional[int] = None

    class Config:
        from_attributes = True

class DrugResponse(BaseModel):
    drug_id: int
    name: str
    description: Optional[str]
    stock_level: Optional[int]
    created_at: datetime
    updated_at: Optional[datetime]

    class Config:
        from_attributes = True

# ----------------------------------- Appointment Schedule Schemas -----------------------------------
class ScheduleBooking(BaseModel):
    schedule_id: int

    class Config:
        from_attributes = True

class AppointmentScheduleCreate(BaseModel):
    availability_id: int
    date: date
    start_time: time
    end_time: time

    @validator('date')
    def validate_date_not_in_past(cls, v):
        if v < datetime.now().date():
            raise ValueError("Date cannot be in the past")
        return v

    class Config:
        from_attributes = True

class AppointmentScheduleUpdate(BaseModel):
    availability_id: Optional[int]
    date: Optional[date]
    start_time: Optional[time]
    end_time: Optional[time]

    class Config:
        from_attributes = True

class AppointmentScheduleResponse(BaseModel):
    schedule_id: int
    doctor_id: str
    student_id: Optional[int]  # Changed from str to int
    availability_id: Optional[int]
    start_time: time
    end_time: time
    date: date
    status: AppointmentStatus
    created_at: datetime
    day_of_week: str

    class Config:
        from_attributes = True


# ----------------------------------- Availability Schemas -----------------------------------
class AvailabilityCreate(BaseModel):
    day_of_week: DayOfWeek
    start_time: time
    end_time: time
    status: Optional[AvailabilityStatus] = AvailabilityStatus.active

    class Config:
        from_attributes = True


class AvailabilityUpdate(BaseModel):
    day_of_week: Optional[DayOfWeek] = None
    start_time: Optional[time] = None
    end_time: Optional[time] = None
    status: Optional[AvailabilityStatus] = None

    class Config:
        from_attributes = True

class AvailabilityResponse(BaseModel):
    availability_id: int
    doctor_id: str
    day_of_week: DayOfWeek
    start_time: time
    end_time: time
    status: AvailabilityStatus
    created_at: datetime

    class Config:
        from_attributes = True

# ----------------------------------- Faculty Schemas -----------------------------------
class FacultyCreate(BaseModel):
    faculty_name: str
    faculty_type: FacultyType

    class Config:
        from_attributes = True


class FacultyUpdate(BaseModel):
    faculty_name: Optional[str] = None
    faculty_type: Optional[FacultyType] = None

    class Config:
        from_attributes = True


class FacultyResponse(BaseModel):
    faculty_id: int
    faculty_name: str
    faculty_type: FacultyType
    created_at: datetime
    updated_at: Optional[datetime]

    class Config:
        from_attributes = True

# ----------------------------------- Department Schemas -----------------------------------
class DepartmentCreate(BaseModel):
    faculty_id: int
    department_name: str

    class Config:
        from_attributes = True

class DepartmentUpdate(BaseModel):
    faculty_id: Optional[int] = None
    department_name: Optional[str] = None

    class Config:
        from_attributes = True

class DepartmentResponse(BaseModel):
    department_id: int
    faculty_id: int
    department_name: str
    faculty_name: str  # Add this field
    created_at: datetime
    updated_at: Optional[datetime]

    class Config:
        from_attributes = True

class GeneralDepartmentResponse(BaseModel):
    department_id: int
    faculty_id: int
    department_name: str
    created_at: datetime
    updated_at: Optional[datetime]

    class Config:
        from_attributes = True

# ----------------------------------- Level Schemas -----------------------------------
class LevelCreate(BaseModel):
    level_name: str

    class Config:
        from_attributes = True

class LevelUpdate(BaseModel):
    level_name: Optional[str] = None

    class Config:
        from_attributes = True

class LevelResponse(BaseModel):
    level_id: int
    level_name: str
    created_at: datetime
    updated_at: Optional[datetime]

    class Config:
        from_attributes = True

# ----------------------------------- Academic Session Schemas -----------------------------------
class AcademicSessionCreate(BaseModel):
    session_name: str

    class Config:
        from_attributes = True

class AcademicSessionUpdate(BaseModel):
    session_name: Optional[str] = None

    class Config:
        from_attributes = True

class AcademicSessionResponse(BaseModel):
    session_id: int
    session_name: str
    created_at: datetime
    updated_at: Optional[datetime]

    class Config:
        from_attributes = True

# ----------------------------------- Generic Response Schemas -----------------------------------
class MessageResponse(BaseModel):
    detail: str

    class Config:
        from_attributes = True


# --------------------------------------------------------------------------------------------------------------------
class StudentInfoOut(BaseModel):
    student_id: int
    full_name: str
    matric_number: str
    gender: Gender
    faculty: str
    department: str
    level: str

class ComplaintOut(BaseModel):
    complaint_description: str
    created_at: datetime

class PrescriptionOut(BaseModel):
    prescription_id: int
    drug_id: int
    drug_name: str
    dosage: str
    instructions: Optional[str]

class DiagnosisOut(BaseModel):
    diagnosis_id: int
    diagnosis_description: str
    treatment_plan: Optional[str]
    prescriptions: List[PrescriptionOut]

class VisitDetailResponse(BaseModel):
    visit_id: int
    visit_date: date
    status: VisitStatus
    student: StudentInfoOut
    complaints: ComplaintOut
    diagnosis: Optional[DiagnosisOut]


# --- Nested Schemas for Relationships (only what's needed) ---

class AcademicSessionBase(BaseModel):
    session_name: str

    class Config:
        from_attributes = True


class FacultyBase(BaseModel):
    faculty_name: str

    class Config:
        from_attributes = True


class DepartmentBase(BaseModel):
    department_name: str

    class Config:
        from_attributes = True


class LevelBase(BaseModel):
    level_name: str

    class Config:
        from_attributes = True


class HealthRecordBase(BaseModel):
    health_record_id: int
    blood_group: Optional[BloodGroup]
    genotype: Optional[Genotype]
    height: Optional[float]
    weight: Optional[float]
    test_date: date
    notes: Optional[str]

    # lab_attendant_id is usually not needed on the student profile itself

    class Config:
        from_attributes = True
        use_enum_values = True  # Return enum values as strings


class ClinicCardBase(BaseModel):
    card_id: int
    clinic_number: str
    issue_date: date
    expiry_date: Optional[date]
    status: CardStatus

    # qr_code will be added dynamically in the endpoint

    class Config:
        from_attributes = True
        use_enum_values = True  # Return enum values as strings


# --- Comprehensive Student Profile Schema ---

class StudentProfileFullSchema(BaseModel):
    # Core Student Fields
    student_id: int
    matriculation_number: str
    first_name: str
    surname: str
    email: EmailStr
    phone: str
    date_of_birth: date
    gender: Gender
    address: Optional[str] = None
    role: str
    emergency_contact: Optional[str] = None
    profile_picture: Optional[str] = None
    status: StudentStatus
    created_at: datetime
    updated_at: Optional[datetime] = None
    last_login: Optional[datetime] = None

    # Relationship Fields (nested models)
    academic_session: Optional[AcademicSessionBase] = None
    faculty: Optional[FacultyBase] = None
    department: Optional[DepartmentBase] = None
    level: Optional[LevelBase] = None

    # Latest Health Record (Optional, if no records exist)
    latest_health_record: Optional[HealthRecordBase] = None

    # Latest/Active Clinic Card (Optional, if no cards exist)
    latest_clinic_card: Optional[ClinicCardBase] = None
    qr_code: Optional[str] = None

    full_name: str  # "Surname Firstname"

    class Config:
        from_attributes = True  # Allow Pydantic to read from SQLAlchemy models
        use_enum_values = True  # Return enum values as strings
        # You might need to adjust json_encoders for date/datetime objects if not handled automatically
        # by FastAPI's default JSON encoder, but typically they are fine.



class VisitResponse(BaseModel):
    visit_id: int
    schedule_id: Optional[int]
    doctor_id: str
    doctor_name: str
    student_id: int
    visit_date: date
    complaint_description: Optional[str]
    status: VisitStatus
    created_at: datetime

    class Config:
        from_attributes = True


class VisitListResponse(BaseModel):
    visit_id: int
    doctor_id: str
    doctor_name: Optional[str]  # Changed to Optional to handle nulls
    visit_date: date
    status: VisitStatus
    complaint_description: Optional[str]

    class Config:
        from_attributes = True


class DrugGivenView(BaseModel):
    drug_name: Optional[str]
    quantity: str
    dispense_date: date

    class Config:
        from_attributes = True

class DispensationView(BaseModel):
    pharmacist_name: Optional[str]
    dispensation_date: datetime
    drugs_given: List[DrugGivenView]

    class Config:
        from_attributes = True

class PrescriptionView(BaseModel):
    drug_name: Optional[str]
    dosage: str
    instructions: Optional[str]
    dispensations: List[DispensationView] = []

    class Config:
        from_attributes = True

class DiagnosisView(BaseModel):
    diagnosis_id: Optional[int]
    diagnosis_description: str
    treatment_plan: Optional[str]
    created_at: Optional[datetime]

    class Config:
        from_attributes = True

class ComplaintView(BaseModel):
    complaint_id: Optional[int]
    description: Optional[str]
    created_at: Optional[datetime]

    class Config:
        from_attributes = True

class VisitDetailedResponse(BaseModel):
    visit_id: int
    schedule_id: Optional[int]
    doctor_id: str
    doctor_name: Optional[str]
    visit_date: date
    status: VisitStatus
    created_at: datetime
    complaint: Optional[ComplaintView]
    diagnosis: Optional[DiagnosisView]
    prescriptions: List[PrescriptionView]

    class Config:
        from_attributes = True


class AppointmentScheduledResponse(BaseModel):
    schedule_id: int
    doctor_id: str
    doctor_name: str
    availability_id: Optional[int]
    student_id: Optional[int]
    date: date
    start_time: time
    end_time: time
    status: AppointmentStatus
    created_at: datetime

    class Config:
        from_attributes = True

# =================================================================================================================

class DoctorInfo(BaseModel):
    doctor_id: str
    name: str
    email: Optional[str]
    phone: Optional[str]

class StudentDashboardResponse(BaseModel):
    total_visits: int
    pending_visits: int
    active_doctors: List[DoctorInfo]

class AdminDashboardResponse(BaseModel):
    total_students: int
    total_users: int
    total_doctors: int
    total_available_drugs: int

class PendingVisit(BaseModel):
    visit_id: int
    student_name: str
    visit_date: date
    matric_number: str

class AppointmentInfo(BaseModel):
    schedule_id: int
    student_name: str
    date: date
    time: str
    matric_number: str

class DoctorDashboardResponse(BaseModel):
    pending_visits: List[PendingVisit]
    total_completed_visits: int
    upcoming_appointments: List[AppointmentInfo]


class DoctorPendingVisitResponse(BaseModel):
    visit_id: int
    student_id: int
    student_name: str
    matric_number: str
    visit_date: date
    time_slot: str  # Format: "HH:MM - HH:MM"
    complaint_id: int
    complaint_description: str
    schedule_id: Optional[int]

    class Config:
        from_attributes = True



# ======================================================================================================================
class FacultyResponses(BaseModel):
    faculty_id: int
    faculty_name: str
    class Config:
        from_attributes = True

class DepartmentResponses(BaseModel):
    department_id: int
    department_name: str
    class Config:
        from_attributes = True

class LevelResponses(BaseModel):
    level_id: int
    level_name: str
    class Config:
        from_attributes = True

class StudentWithRelationResponse(BaseModel):
    student_id: int
    first_name: str
    surname: str
    matriculation_number: str
    department: Optional[DepartmentResponses]
    faculty: Optional[FacultyResponses]
    level: Optional[LevelResponses]
    email: str
    phone: Optional[str]
    date_of_birth: date
    gender: str
    emergency_contact: Optional[str]
    class Config:
        from_attributes = True

class PrescriptionsResponse(BaseModel):
    prescription_id: int
    diagnosis_id: int
    student_id: int
    doctor_id: str
    drug_id: int
    drug_name: str
    dosage: str
    instructions: Optional[str]
    visit_id: int
    visit_date: date
    created_at: datetime
    class Config:
        from_attributes = True

class SimpleDrug(BaseModel):
    name: str
    drug_id: int

class DispensationsView(BaseModel):
    dispensation_id: int
    drug_given_id: int
    drug: SimpleDrug
    quantity: int
    dispense_date: date
    pharmacist_name: str
    class Config:
        from_attributes = True

class DrugDispensationsCreate(BaseModel):
    prescription_id: int
    student_id: int
    drug_id: int
    quantity: str
    dispense_date: date

class DrugDispensationsResponse(BaseModel):
    dispensation_id: int
    prescription_id: int
    student_id: int
    pharmacist_id: str
    created_at: datetime
    class Config:
        from_attributes = True

# class DrugCreate(BaseModel):
#     name: str
#     description: Optional[str]
#     stock_level: int
#
# class DrugUpdate(BaseModel):
#     name: Optional[str]
#     description: Optional[str]
#     stock_level: Optional[int]

# class MessageResponse(BaseModel):
#     detail: str




