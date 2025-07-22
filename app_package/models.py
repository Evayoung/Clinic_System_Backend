from sqlalchemy import Column, Integer, String, TIMESTAMP, Date, func, ForeignKey, Float, Text, Time, Enum, UniqueConstraint
from sqlalchemy.orm import relationship
from sqlalchemy.ext.declarative import declarative_base
from .database import Base
import enum

# Enums
class UserStatus(enum.Enum):
    active = "active"
    inactive = "inactive"

class UserRole(enum.Enum):
    doctor = "doctor"
    admin = "admin"
    pharmacist = "pharmacist"
    lab_attendant = "lab_attendant"

class StudentStatus(enum.Enum):
    active = "active"
    inactive = "inactive"

# class BloodGroup(enum.Enum):
#     A_positive = "A+"
#     A_negative = "A-"
#     B_positive = "B+"
#     B_negative = "B-"
#     AB_positive = "AB+"
#     AB_negative = "AB-"
#     O_positive = "O+"
#     O_negative = "O-"

class BloodGroup(str, enum.Enum):
    A_positive = "A+"
    A_negative = "A-"
    B_positive = "B+"
    B_negative = "B-"
    AB_positive = "AB+"
    AB_negative = "AB-"
    O_positive = "O+"
    O_negative = "O-"

class Genotype(enum.Enum):
    AA = "AA"
    AS = "AS"
    SS = "SS"
    AC = "AC"
    SC = "SC"

class CardStatus(enum.Enum):
    active = "active"
    inactive = "inactive"

class VisitStatus(enum.Enum):
    pending = "pending"
    completed = "completed"
    cancelled = "cancelled"

class AppointmentStatus(enum.Enum):
    available = "available"
    booked = "booked"
    completed = "completed"
    cancelled = "cancelled"
    pending = "pending"

class AvailabilityStatus(enum.Enum):
    active = "active"
    inactive = "inactive"

class DayOfWeek(enum.Enum):
    Monday = "Monday"
    Tuesday = "Tuesday"
    Wednesday = "Wednesday"
    Thursday = "Thursday"
    Friday = "Friday"
    Saturday = "Saturday"
    Sunday = "Sunday"

class Gender(enum.Enum):
    male = "male"
    female = "female"
    other = "other"

class User(Base):
    """User Data Model"""
    __tablename__ = "users"
    user_id = Column(String, primary_key=True, nullable=False, unique=True)
    username = Column(String, nullable=False, index=True)
    password = Column(String, nullable=False)
    role = Column(Enum(UserRole), nullable=False, index=True)
    email = Column(String, unique=True, nullable=False, index=True)
    phone = Column(String, nullable=True, index=True)
    status = Column(Enum(UserStatus), nullable=False, default="active", index=True)
    created_at = Column(TIMESTAMP(timezone=True), nullable=False, server_default=func.now())
    updated_at = Column(TIMESTAMP(timezone=True), nullable=True, onupdate=func.now())
    last_login = Column(TIMESTAMP(timezone=True), nullable=True)

    health_records = relationship("HealthRecord", back_populates="lab_attendant")
    visits = relationship("ClinicVisit", back_populates="doctor")
    # complaints = relationship("StudentComplaint", back_populates="doctor")
    diagnoses = relationship("DoctorDiagnosis", back_populates="doctor")
    prescriptions = relationship("DoctorPrescription", back_populates="doctor")
    dispensations = relationship("DrugDispensation", back_populates="pharmacist")
    schedules = relationship("AppointmentSchedule", back_populates="doctor")
    availabilities = relationship("Availability", back_populates="doctor")
    access_logs = relationship("AccessLog", back_populates="user")

class Student(Base):
    """Student Data Model"""
    __tablename__ = "students"
    student_id = Column(Integer, primary_key=True, autoincrement=True, nullable=False)
    matriculation_number = Column(String, unique=True, nullable=False, index=True)
    first_name = Column(String, nullable=False, index=True)
    surname = Column(String, nullable=False, index=True)
    email = Column(String, unique=True, nullable=False, index=True)
    session_id = Column(Integer, ForeignKey("academic_sessions.session_id"), nullable=False, index=True)
    phone = Column(String, nullable=False, index=True)
    date_of_birth = Column(Date, nullable=False)
    gender = Column(Enum(Gender), nullable=False)
    address = Column(String, nullable=True)
    role = Column(String, nullable=False, default="student")
    password = Column(String, nullable=False)
    faculty_id = Column(Integer, ForeignKey("faculties.faculty_id"), nullable=False, index=True)
    department_id = Column(Integer, ForeignKey("departments.department_id"), nullable=False, index=True)
    level_id = Column(Integer, ForeignKey("levels.level_id"), nullable=False, index=True)
    emergency_contact = Column(String, nullable=True, index=True)
    profile_picture = Column(String, nullable=True)
    status = Column(Enum(StudentStatus), nullable=False, default="active", index=True)
    created_at = Column(TIMESTAMP(timezone=True), nullable=False, server_default=func.now())
    updated_at = Column(TIMESTAMP(timezone=True), nullable=True, onupdate=func.now())
    last_login = Column(TIMESTAMP(timezone=True), nullable=True)

    academic_session = relationship("AcademicSession", back_populates="students")
    faculty = relationship("Faculty", back_populates="students")
    department = relationship("Department", back_populates="students")
    level = relationship("Level", back_populates="students")
    health_records = relationship("HealthRecord", back_populates="student")
    digital_cards = relationship("ClinicCard", back_populates="student")
    visits = relationship("ClinicVisit", back_populates="student")
    complaints = relationship("StudentComplaint", back_populates="student")
    diagnoses = relationship("DoctorDiagnosis", back_populates="student")
    prescriptions = relationship("DoctorPrescription", back_populates="student")
    dispensations = relationship("DrugDispensation", back_populates="student")
    schedules = relationship("AppointmentSchedule", back_populates="student")
    access_logs = relationship("AccessLog", back_populates="student")

class HealthRecord(Base):
    """Health Record Data Model"""

    __tablename__ = "health_records"
    health_record_id = Column(Integer, primary_key=True, autoincrement=True, nullable=False)
    student_id = Column(Integer, ForeignKey("students.student_id"), nullable=False, index=True)
    blood_group = Column(Enum(BloodGroup), nullable=True, index=True)
    genotype = Column(Enum(Genotype), nullable=True, index=True)
    height = Column(Float, nullable=True)
    weight = Column(Float, nullable=True)
    test_date = Column(Date, nullable=False)
    lab_attendant_id = Column(String, ForeignKey("users.user_id"), nullable=False, index=True)
    notes = Column(Text, nullable=True)
    created_at = Column(TIMESTAMP(timezone=True), nullable=False, server_default=func.now())
    updated_at = Column(TIMESTAMP(timezone=True), nullable=True, onupdate=func.now())

    student = relationship("Student", back_populates="health_records")
    lab_attendant = relationship("User", back_populates="health_records")

class ClinicCard(Base):
    """Clinic Card Data Model"""
    __tablename__ = "digital_cards"
    card_id = Column(Integer, primary_key=True, autoincrement=True, nullable=False)
    student_id = Column(Integer, ForeignKey("students.student_id"), nullable=False, index=True)
    clinic_number = Column(String, unique=True, nullable=False, index=True)
    issue_date = Column(Date, nullable=False)
    expiry_date = Column(Date, nullable=True)
    status = Column(Enum(CardStatus), nullable=False, default="active", index=True)
    created_at = Column(TIMESTAMP(timezone=True), nullable=False, server_default=func.now())
    updated_at = Column(TIMESTAMP(timezone=True), nullable=True, onupdate=func.now())

    student = relationship("Student", back_populates="digital_cards")

class ClinicVisit(Base):
    """Clinic Visit Data Model"""
    __tablename__ = "clinic_visits"
    visit_id = Column(Integer, primary_key=True, autoincrement=True, nullable=False)
    student_id = Column(Integer, ForeignKey("students.student_id"), nullable=False, index=True)
    doctor_id = Column(String, ForeignKey("users.user_id"), nullable=False, index=True)
    schedule_id = Column(Integer, ForeignKey("appointment_schedules.schedule_id"), nullable=True, index=True)
    visit_date = Column(Date, nullable=False)
    status = Column(Enum(VisitStatus), nullable=False, default="pending", index=True)
    created_at = Column(TIMESTAMP(timezone=True), nullable=False, server_default=func.now())

    student = relationship("Student", back_populates="visits")
    doctor = relationship("User", back_populates="visits")
    schedule = relationship("AppointmentSchedule", back_populates="visits")
    complaints = relationship("StudentComplaint", back_populates="visit")
    diagnoses = relationship("DoctorDiagnosis", back_populates="visit")


class StudentComplaint(Base):
    """Complaint Data Model"""
    __tablename__ = "complaints"
    complaint_id = Column(Integer, primary_key=True, autoincrement=True, nullable=False)
    visit_id = Column(Integer, ForeignKey("clinic_visits.visit_id"), nullable=False, index=True)
    student_id = Column(Integer, ForeignKey("students.student_id"), nullable=False, index=True)
    complaint_description = Column(Text, nullable=False)
    created_at = Column(TIMESTAMP(timezone=True), nullable=False, server_default=func.now())

    visit = relationship("ClinicVisit", back_populates="complaints")
    student = relationship("Student", back_populates="complaints")
    diagnoses = relationship("DoctorDiagnosis", back_populates="complaints")


class DoctorDiagnosis(Base):
    """Diagnosis Data Model"""
    __tablename__ = "diagnoses"
    diagnosis_id = Column(Integer, primary_key=True, autoincrement=True, nullable=False)
    visit_id = Column(Integer, ForeignKey("clinic_visits.visit_id"), nullable=False, index=True)
    student_id = Column(Integer, ForeignKey("students.student_id"), nullable=False, index=True)
    complaint_id = Column(Integer, ForeignKey("complaints.complaint_id"), nullable=False, index=True)
    doctor_id = Column(String, ForeignKey("users.user_id"), nullable=False, index=True)
    diagnosis_description = Column(Text, nullable=False)
    treatment_plan = Column(Text, nullable=True)
    created_at = Column(TIMESTAMP(timezone=True), nullable=False, server_default=func.now())

    visit = relationship("ClinicVisit", back_populates="diagnoses")
    student = relationship("Student", back_populates="diagnoses")
    doctor = relationship("User", back_populates="diagnoses")
    complaints = relationship("StudentComplaint", back_populates="diagnoses")
    prescriptions = relationship("DoctorPrescription", back_populates="diagnosis")


class DoctorPrescription(Base):
    """Prescription Data Model"""
    __tablename__ = "prescriptions"
    prescription_id = Column(Integer, primary_key=True, autoincrement=True, nullable=False)
    diagnosis_id = Column(Integer, ForeignKey("diagnoses.diagnosis_id"), nullable=False, index=True)
    student_id = Column(Integer, ForeignKey("students.student_id"), nullable=False, index=True)
    doctor_id = Column(String, ForeignKey("users.user_id"), nullable=False, index=True)
    drug_id = Column(Integer, ForeignKey("drugs.drug_id"), nullable=False, index=True)
    dosage = Column(String, nullable=False)
    instructions = Column(Text, nullable=True)
    created_at = Column(TIMESTAMP(timezone=True), nullable=False, server_default=func.now())

    diagnosis = relationship("DoctorDiagnosis", back_populates="prescriptions")
    student = relationship("Student", back_populates="prescriptions")
    doctor = relationship("User", back_populates="prescriptions")
    drug = relationship("Drugs", back_populates="prescriptions")
    dispensations = relationship("DrugDispensation", back_populates="prescription")

class DrugDispensation(Base):
    """Drug Dispensation Data Model"""
    __tablename__ = "drug_dispensations"
    dispensation_id = Column(Integer, primary_key=True, autoincrement=True, nullable=False)
    prescription_id = Column(Integer, ForeignKey("prescriptions.prescription_id"), nullable=False, index=True)
    student_id = Column(Integer, ForeignKey("students.student_id"), nullable=False, index=True)
    pharmacist_id = Column(String, ForeignKey("users.user_id"), nullable=False, index=True)
    created_at = Column(TIMESTAMP(timezone=True), nullable=False, server_default=func.now())

    prescription = relationship("DoctorPrescription", back_populates="dispensations")
    student = relationship("Student", back_populates="dispensations")
    pharmacist = relationship("User", back_populates="dispensations")
    drugs_given = relationship("DispensedDrugs", back_populates="dispensations")


class DispensedDrugs(Base):
    """Drug Dispensed To Student Data Model"""
    __tablename__ = "drug_given"
    drug_given_id = Column(Integer, primary_key=True, autoincrement=True, nullable=False)
    prescription_id = Column(Integer, ForeignKey("drug_dispensations.dispensation_id"), nullable=False, index=True)
    drug_id = Column(Integer, ForeignKey("drugs.drug_id"), nullable=False, index=True)
    quantity = Column(String, nullable=False)
    dispense_date = Column(Date, nullable=False)

    dispensations = relationship("DrugDispensation", back_populates="drugs_given")
    drug = relationship("Drugs", back_populates="drugs_given")

class Drugs(Base):
    """Drug Data Model"""
    __tablename__ = "drugs"
    drug_id = Column(Integer, primary_key=True, autoincrement=True, nullable=False)
    name = Column(String, unique=True, nullable=False, index=True)
    description = Column(Text, nullable=True)
    stock_level = Column(Integer, nullable=True)
    created_at = Column(TIMESTAMP(timezone=True), nullable=False, server_default=func.now())
    updated_at = Column(TIMESTAMP(timezone=True), nullable=True, onupdate=func.now())

    prescriptions = relationship("DoctorPrescription", back_populates="drug")
    # dispensations = relationship("DrugDispensation", back_populates="drug")
    drugs_given = relationship("DispensedDrugs", back_populates="drug")

class AppointmentSchedule(Base):
    """Appointment Schedule Data Model"""
    __tablename__ = "appointment_schedules"
    schedule_id = Column(Integer, primary_key=True, autoincrement=True, nullable=False)
    doctor_id = Column(String, ForeignKey("users.user_id"), nullable=False, index=True)
    student_id = Column(Integer, ForeignKey("students.student_id"), nullable=True, index=True)
    availability_id = Column(Integer, ForeignKey("availabilities.availability_id"), nullable=True, index=True)
    start_time = Column(Time, nullable=False)
    end_time = Column(Time, nullable=False)
    date = Column(Date, nullable=False)
    status = Column(Enum(AppointmentStatus), nullable=False, default=AppointmentStatus.available, index=True)
    created_at = Column(TIMESTAMP(timezone=True), nullable=False, server_default=func.now())

    doctor = relationship("User", back_populates="schedules")
    student = relationship("Student", back_populates="schedules")
    availability = relationship("Availability", back_populates="schedules")
    visits = relationship("ClinicVisit", back_populates="schedule")


class Availability(Base):
    """Availability Data Model"""
    __tablename__ = "availabilities"
    availability_id = Column(Integer, primary_key=True, autoincrement=True, nullable=False)
    doctor_id = Column(String, ForeignKey("users.user_id"), nullable=False, index=True)
    day_of_week = Column(Enum(DayOfWeek), nullable=False, index=True)
    start_time = Column(Time, nullable=False)
    end_time = Column(Time, nullable=False)
    status = Column(Enum(AvailabilityStatus), nullable=False, default="active", index=True)
    created_at = Column(TIMESTAMP(timezone=True), nullable=False, server_default=func.now())

    doctor = relationship("User", back_populates="availabilities")
    schedules = relationship("AppointmentSchedule", back_populates="availability")

class Faculty(Base):
    """Faculty Data Model"""
    __tablename__ = "faculties"
    faculty_id = Column(Integer, primary_key=True, autoincrement=True, nullable=False)
    faculty_name = Column(String, unique=True, nullable=False, index=True)
    faculty_type = Column(String, nullable=False, index=True)
    created_at = Column(TIMESTAMP(timezone=True), nullable=False, server_default=func.now())
    updated_at = Column(TIMESTAMP(timezone=True), nullable=True, onupdate=func.now())

    departments = relationship("Department", back_populates="faculty")
    students = relationship("Student", back_populates="faculty")

class Department(Base):
    """Department Data Model"""
    __tablename__ = "departments"
    department_id = Column(Integer, primary_key=True, autoincrement=True, nullable=False)
    faculty_id = Column(Integer, ForeignKey("faculties.faculty_id"), nullable=False, index=True)
    department_name = Column(String, nullable=False, index=True)
    created_at = Column(TIMESTAMP(timezone=True), nullable=False, server_default=func.now())
    updated_at = Column(TIMESTAMP(timezone=True), nullable=True, onupdate=func.now())
    __table_args__ = (UniqueConstraint("faculty_id", "department_name", name="uq_faculty_department"),)

    faculty = relationship("Faculty", back_populates="departments")
    students = relationship("Student", back_populates="department")

class Level(Base):
    """Level Data Model"""
    __tablename__ = "levels"
    level_id = Column(Integer, primary_key=True, autoincrement=True, nullable=False)
    level_name = Column(String, unique=True, nullable=False, index=True)
    created_at = Column(TIMESTAMP(timezone=True), nullable=False, server_default=func.now())
    updated_at = Column(TIMESTAMP(timezone=True), nullable=True, onupdate=func.now())

    students = relationship("Student", back_populates="level")

class AcademicSession(Base):
    """Academic Session Data Model"""
    __tablename__ = "academic_sessions"
    session_id = Column(Integer, primary_key=True, autoincrement=True, nullable=False)
    session_name = Column(String, unique=True, nullable=False, index=True)
    created_at = Column(TIMESTAMP(timezone=True), nullable=False, server_default=func.now())
    updated_at = Column(TIMESTAMP(timezone=True), nullable=True, onupdate=func.now())

    students = relationship("Student", back_populates="academic_session")

class AccessLog(Base):
    """Access Log Data Model"""
    __tablename__ = "access_logs"
    log_id = Column(Integer, primary_key=True, autoincrement=True, nullable=False)
    user_id = Column(String, ForeignKey("users.user_id"), nullable=True, index=True)
    student_id = Column(Integer, ForeignKey("students.student_id"), nullable=True, index=True)
    action = Column(String, nullable=False)
    timestamp = Column(TIMESTAMP(timezone=True), nullable=False, server_default=func.now())
    ip_address = Column(String, nullable=True)
    created_at = Column(TIMESTAMP(timezone=True), nullable=False, server_default=func.now())

    user = relationship("User", back_populates="access_logs")
    student = relationship("Student", back_populates="access_logs")