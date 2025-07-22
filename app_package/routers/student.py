from enum import Enum

import aiofiles

from sqlalchemy.orm import selectinload, joinedload  # Important for eager loading relationshipsn
import io # For QR code generation
from PIL import Image

from fastapi import APIRouter, Depends, status, HTTPException, Request
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from datetime import datetime, date
from typing import List, Union, Optional
from pathlib import Path
import qrcode
from io import BytesIO
import base64


from .. import utils, models, oauth2, database, schemas

router = APIRouter(
    prefix="/students",
    tags=["Student"]
)

# async def log_access(db: AsyncSession, user_id: str, student_id: int, action: str, ip_address: str):
#     access_log = models.AccessLog(
#         user_id=user_id,
#         student_id=student_id,
#         action=action,
#         ip_address=ip_address,
#         timestamp=datetime.utcnow()
#     )
#     db.add(access_log)
#     await db.commit()


@router.post("/create-students", response_model=schemas.StudentResponse, status_code=status.HTTP_201_CREATED)
async def create_student(
    student: schemas.StudentCreate,
    db: AsyncSession = Depends(database.get_db)
):
    try:
        # Check matriculation_number or email exists
        result = await db.execute(
            select(models.Student).filter(
                (models.Student.matriculation_number == student.matriculation_number) |
                (models.Student.email == student.email)
            )
        )
        if result.scalar_one_or_none():
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Matriculation number or email already exists")

        # Validate foreign keys
        result = await db.execute(select(models.Faculty).filter(models.Faculty.faculty_id == student.faculty_id))
        if not result.scalar_one_or_none():
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid faculty_id")

        result = await db.execute(select(models.Department).filter(models.Department.department_id == student.department_id))
        if not result.scalar_one_or_none():
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid department_id")

        result = await db.execute(select(models.Level).filter(models.Level.level_id == student.level_id))
        if not result.scalar_one_or_none():
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid level_id")

        result = await db.execute(select(models.AcademicSession).filter(models.AcademicSession.session_id == student.session_id))
        if not result.scalar_one_or_none():
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid session_id")

        # Hash password
        hashed_password = await utils.hash_password(student.password)

        # Handle profile picture
        profile_picture_path = None
        if student.profile_picture:
            try:
                # Remove data URL prefix if present (e.g., "data:image/jpeg;base64,")
                profile_picture_base64 = student.profile_picture
                if "," in profile_picture_base64:
                    profile_picture_base64 = profile_picture_base64.split(",")[1]

                # Basic validation of Base64 string
                try:
                    base64.b64decode(profile_picture_base64, validate=True)
                except Exception as e:
                    raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"Invalid Base64 data for profile picture: {str(e)}")

                # Replace '/' with '-' in matriculation number for file naming
                pics_name = student.matriculation_number.replace("/", "-")
                # Create images directory if it doesn't exist
                Path("images").mkdir(parents=True, exist_ok=True)
                profile_picture_path = f"images/{pics_name}.jpg"
                async with aiofiles.open(profile_picture_path, "wb") as file_object:
                    await file_object.write(base64.b64decode(profile_picture_base64))
            except Exception as e:
                raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"Failed to process profile picture: {str(e)}")

        # Create student
        new_student = models.Student(
            matriculation_number=student.matriculation_number,
            first_name=student.first_name,
            surname=student.surname,
            email=student.email,
            session_id=student.session_id,
            phone=student.phone,
            date_of_birth=student.date_of_birth,
            gender=student.gender,
            address=student.address,
            role=student.role,
            password=hashed_password,
            faculty_id=student.faculty_id,
            department_id=student.department_id,
            level_id=student.level_id,
            emergency_contact=student.emergency_contact,
            profile_picture=profile_picture_path,
            status=student.status
        )
        db.add(new_student)
        await db.commit()
        await db.refresh(new_student)

        # Generate digital card
        clinic_number = await utils.generate_clinic_number(db)
        new_card = models.ClinicCard(
            student_id=new_student.student_id,
            clinic_number=clinic_number,
            issue_date=datetime.utcnow().date(),
            status=models.CardStatus.active
        )
        db.add(new_card)
        await db.commit()

        return new_student

    except Exception as e:
        await db.rollback()
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"Failed to create student: {str(e)}")



# Helper to generate QR Code as Base64 string
def generate_qr_code_base64(data: str) -> str:
    qr = qrcode.QRCode(
        version=1,
        error_correction=qrcode.constants.ERROR_CORRECT_L,
        box_size=10,
        border=4,
    )
    qr.add_data(data)
    qr.make(fit=True)

    img = qr.make_image(fill_color="black", back_color="white").convert('RGB')

    # Save image to a bytes buffer
    buffered = io.BytesIO()
    img.save(buffered, format="PNG")  # Use PNG for transparency if needed, or JPEG
    img_str = base64.b64encode(buffered.getvalue()).decode("utf-8")
    return f"data:image/png;base64,{img_str}"  # Data URL format


@router.get("/full-profile", response_model=schemas.StudentProfileFullSchema, status_code=status.HTTP_200_OK)
async def get_full_student_profile(
        current_user: schemas.StudentResponse = Depends(oauth2.get_current_user),
        db: AsyncSession = Depends(database.get_db)
):
    # Eagerly load all necessary relationships to get data in one query
    result = await db.execute(
        select(models.Student)
        .options(
            selectinload(models.Student.academic_session),
            selectinload(models.Student.faculty),
            selectinload(models.Student.department),
            selectinload(models.Student.level),
            selectinload(models.Student.health_records),  # This will load all health records
            selectinload(models.Student.digital_cards),  # This will load all digital cards
        )
        .filter(models.Student.matriculation_number == current_user.matriculation_number)
    )
    student = result.scalar_one_or_none()

    if not student:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Student not found.")

    # Get the latest HealthRecord
    latest_health_record = None
    if student.health_records:
        # Sort health records by test_date in descending order to get the latest
        latest_health_record = sorted(
            student.health_records,
            key=lambda hr: hr.test_date if hr.test_date else date.min,  # Handle potential None dates
            reverse=True
        )[0]

    # Get the latest/active ClinicCard
    latest_clinic_card = None
    qr_code_base64 = None
    if student.digital_cards:
        # Sort clinic cards by issue_date in descending order to get the latest
        latest_clinic_card = sorted(
            student.digital_cards,
            key=lambda cc: cc.issue_date if cc.issue_date else date.min,  # Handle potential None dates
            reverse=True
        )[0]

        # Generate QR code for the clinic number
        if latest_clinic_card and latest_clinic_card.clinic_number:
            qr_code_base64 = generate_qr_code_base64(latest_clinic_card.clinic_number)

    # Prepare the response data, mapping SQLAlchemy models to Pydantic schema
    # Use .dict() for Pydantic models that are already loaded, or access attributes directly
    response_data = {
        **student.__dict__,  # Unpack basic student attributes
        "academic_session": student.academic_session,  # Pydantic will pick 'session_name'
        "faculty": student.faculty,
        "department": student.department,
        "level": student.level,
        "latest_health_record": latest_health_record,
        "latest_clinic_card": latest_clinic_card,
        "qr_code": qr_code_base64,
        "full_name": f"{student.surname.upper()} {student.first_name.upper()}",  # Derived field
    }

    # Clean up SQLAlchemy internal state attributes before passing to Pydantic
    for key in list(response_data.keys()):
        if key.startswith("_sa_"):
            del response_data[key]

    # Explicitly convert Enums to their values if not handled automatically by from_attributes and use_enum_values
    if "gender" in response_data and isinstance(response_data["gender"], Enum):
        response_data["gender"] = response_data["gender"].value
    if "status" in response_data and isinstance(response_data["status"], Enum):
        response_data["status"] = response_data["status"].value

    try:
        # Validate and return the data using the Pydantic schema
        return schemas.StudentProfileFullSchema(**response_data)
    except Exception as e:
        print(f"Error creating response model for student {current_user.matriculation_number}: {e}")
        # print(f"Data that failed: {response_data}") # Uncomment for debugging
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                            detail=f"Failed to process student profile data: {e}")



@router.get("/me", response_model=schemas.StudentResponse)
async def get_current_student(
    current_user: schemas.StudentResponse = Depends(oauth2.get_current_user),
    db: AsyncSession = Depends(database.get_db),
    request: Request = None
):
    if current_user.role != "student":
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Student access required")

    result = await db.execute(
        select(models.Student).filter(models.Student.student_id == current_user.student_id)
    )
    student = result.scalar_one_or_none()

    if not student:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Student not found")

    # await log_access(db, None, student.student_id, "get_student_profile", request.client.host)
    return student

@router.put("/me", response_model=schemas.StudentResponse)
async def update_student(
    student_update: schemas.StudentUpdate,
    current_user: schemas.StudentResponse = Depends(oauth2.get_current_user),
    db: AsyncSession = Depends(database.get_db),
    request: Request = None
):
    if current_user.role != "student":
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Student access required")

    async with db.begin():  # Transaction
        result = await db.execute(
            select(models.Student).filter(models.Student.student_id == current_user.student_id)
        )
        student = result.scalar_one_or_none()

        if not student:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Student not found")

        if student_update.email and student_update.email != student.email:
            result = await db.execute(
                select(models.Student).filter(models.Student.email == student_update.email)
            )
            if result.scalar_one_or_none():
                raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Email already exists")

        update_data = student_update.dict(exclude_unset=True)
        if "password" in update_data:
            update_data["password"] = await utils.hash_password(update_data["password"])
        for key, value in update_data.items():
            setattr(student, key, value)

        await db.commit()
        await db.refresh(student)

    # await log_access(db, None, student.student_id, "update_student_profile", request.client.host)
    return student

@router.get("/me/digital-card", response_model=schemas.ClinicCardResponse)
async def get_digital_card(
    current_user: schemas.StudentResponse = Depends(oauth2.get_current_user),
    db: AsyncSession = Depends(database.get_db),
    request: Request = None
):
    if current_user.role != "student":
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Student access required")

    async with db.begin():
        result = await db.execute(
            select(models.ClinicCard).filter(models.ClinicCard.student_id == current_user.student_id)
        )
        clinic_card = result.scalar_one_or_none()

        if not clinic_card:
            clinic_number = await utils.generate_clinic_number(db)
            new_card = models.ClinicCard(
                student_id=current_user.student_id,
                clinic_number=clinic_number,
                issue_date=datetime.utcnow().date(),
                status=models.CardStatus.active
            )
            db.add(new_card)
            await db.commit()
            await db.refresh(new_card)
            clinic_card = new_card

        # Fetch student's matriculation_number
        result = await db.execute(
            select(models.Student).filter(models.Student.student_id == current_user.student_id)
        )
        student = result.scalar_one_or_none()
        if not student:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Student not found")

        # Generate QR code with matriculation_number
        qr_data = f"ClinicCard:{clinic_card.clinic_number}:{student.matriculation_number}"
        qr = qrcode.QRCode(version=1, box_size=10, border=5)
        qr.add_data(qr_data)
        qr.make(fit=True)
        img = qr.make_image(fill="black", back_color="white")
        buffer = BytesIO()
        img.save(buffer, format="PNG")
        qr_code_base64 = base64.b64encode(buffer.getvalue()).decode("utf-8")
        clinic_card.qr_code = qr_code_base64

    # await log_access(db, None, current_user.student_id, "get_digital_card", request.client.host)
    return clinic_card

@router.post("/visits", response_model=schemas.ClinicVisitResponse, status_code=status.HTTP_201_CREATED)
async def create_visit(
    visit: schemas.ClinicVisitCreate,
    current_user: schemas.StudentResponse = Depends(oauth2.get_current_user),
    db: AsyncSession = Depends(database.get_db),
    request: Request = None
):
    if current_user.role != "student":
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Student access required")

    async with db.begin():  # Transaction
        result = await db.execute(
            select(models.AppointmentSchedule).filter(models.AppointmentSchedule.schedule_id == visit.schedule_id)
        )
        schedule = result.scalar_one_or_none()
        if not schedule:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid schedule_id")

        if visit.visit_date != schedule.date:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Visit date must match schedule date")

        result = await db.execute(
            select(models.ClinicVisit).filter(
                models.ClinicVisit.schedule_id == visit.schedule_id,
                models.ClinicVisit.visit_date == visit.visit_date
            )
        )
        existing_visits = result.scalars().all()
        if existing_visits:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Schedule is already booked")

        new_visit = models.ClinicVisit(
            student_id=current_user.student_id,
            doctor_id=schedule.doctor_id,
            schedule_id=visit.schedule_id,
            visit_date=visit.visit_date,
            status=models.VisitStatus.pending
        )
        db.add(new_visit)
        await db.commit()
        await db.refresh(new_visit)

    # await log_access(db, None, current_user.student_id, "create_visit", request.client.host)
    return new_visit


@router.get("/me/schedules", response_model=List[schemas.AppointmentScheduleResponse])
async def get_student_schedules(
    current_user: schemas.StudentResponse = Depends(oauth2.get_current_user),
    db: AsyncSession = Depends(database.get_db),
    request: Request = None,
    limit: int = 10,
    offset: int = 0
):
    if current_user.role != "student":
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Student access required")

    result = await db.execute(
        select(models.AppointmentSchedule)
        .filter(models.AppointmentSchedule.student_id == current_user.student_id)
        .limit(limit)
        .offset(offset)
    )
    schedules = result.scalars().all()

    # await log_access(db, None, current_user.student_id, "get_schedules", request.client.host)
    return schedules

@router.post("/schedules", response_model=schemas.AppointmentScheduleResponse, status_code=status.HTTP_201_CREATED)
async def book_schedule(
    booking: schemas.ScheduleBooking,
    current_user: schemas.StudentResponse = Depends(oauth2.get_current_user),
    db: AsyncSession = Depends(database.get_db),
    request: Request = None
):
    if current_user.role != "student":
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Student access required")

    async with db.begin():  # Transaction
        # Validate schedule exists and is available
        result = await db.execute(
            select(models.AppointmentSchedule).filter(
                models.AppointmentSchedule.schedule_id == booking.schedule_id,
                models.AppointmentSchedule.student_id.is_(None),
                models.AppointmentSchedule.status == models.AppointmentStatus.booked
            )
        )
        schedule = result.scalar_one_or_none()
        if not schedule:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Schedule not found, already booked, or unavailable"
            )

        # Update schedule with student_id
        schedule.student_id = current_user.student_id
        schedule.updated_at = datetime.utcnow()

        # Create corresponding clinic visit
        new_visit = models.ClinicVisit(
            student_id=current_user.student_id,
            doctor_id=schedule.doctor_id,
            schedule_id=schedule.schedule_id,
            visit_date=schedule.date,
            status=models.VisitStatus.pending
        )
        db.add(new_visit)

        await db.commit()
        await db.refresh(schedule)

    # await log_access(db, None, current_user.student_id, f"book_schedule_{booking.schedule_id}", request.client.host)
    return schedule


@router.get("/me/prescriptions", response_model=List[schemas.PrescriptionResponse])
async def get_student_prescriptions(
    current_user: schemas.StudentResponse = Depends(oauth2.get_current_user),
    db: AsyncSession = Depends(database.get_db),
    request: Request = None
):
    if current_user.role != "student":
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Student access required")

    result = await db.execute(
        select(models.DoctorPrescription).filter(models.DoctorPrescription.student_id == current_user.student_id)
    )
    prescriptions = result.scalars().all()

    # await log_access(db, None, current_user.student_id, "list_prescriptions", request.client.host)
    return prescriptions



@router.get("/faculties", response_model=List[schemas.FacultyResponse])
async def get_faculties(
    db: AsyncSession = Depends(database.get_db),
    request: Request = None,
    limit: int = 100,
    offset: int = 0
):

    result = await db.execute(
        select(models.Faculty).limit(limit).offset(offset)
    )
    faculties = result.scalars().all()

    return faculties


@router.get('/read-department/', response_model=Union[List[schemas.GeneralDepartmentResponse], schemas.GeneralDepartmentResponse])
async def get_department(
        department_id: Optional[str] = None,
        limit: Optional[int] = 150,  # Default limit set to 150
        offset: Optional[int] = 0,  # Default offset set to 0
        db: AsyncSession = Depends(database.get_db),
        faculty: Optional[str] = None,  # Faculty name provided as input
        department_name: Optional[str] = None,
        get_all: Optional[bool] = None
):
    # Start building the query
    query = select(models.Department)

    # Filter by department_id if provided
    if department_id:
        query = query.where(models.Department.department_id == department_id)

    # Handle faculty name -> faculty_id mapping
    if faculty:
        faculty_result = await db.execute(
            select(models.Faculty).where(models.Faculty.faculty_name == faculty)
        )
        faculty_record = faculty_result.scalars().first()
        if not faculty_record:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND,
                               detail=f"Faculty with name '{faculty}' not found!")
        query = query.where(models.Department.faculty_id == faculty_record.faculty_id)

    # Filter by department_name if provided
    if department_name:
        query = query.where(models.Department.department_name.ilike(f'%{department_name}%'))

    # Apply pagination
    query = query.offset(offset).limit(limit)

    # Execute the query and get the results
    result = await db.execute(query)
    departments = result.scalars().all()

    if not departments:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="No departments found!")

    if get_all:
        return departments

    # If a single department was requested by ID, return just that department
    if department_id:
        if len(departments) == 1:
            return departments[0]
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND,
                          detail=f"Department with id '{department_id}' not found!")

    return departments


@router.get("/get-levels", response_model=List[schemas.LevelResponse])
async def get_levels(
    db: AsyncSession = Depends(database.get_db),
    request: Request = None,
    limit: int = 10,
    offset: int = 0
):

    result = await db.execute(
        select(models.Level).limit(limit).offset(offset)
    )
    levels = result.scalars().all()

    return levels

@router.get("/get-sessions", response_model=List[schemas.AcademicSessionResponse])
async def get_sessions(
    db: AsyncSession = Depends(database.get_db),
    request: Request = None,
    limit: int = 100,
    offset: int = 0
):
    try:
        result = await db.execute(
            select(models.AcademicSession).limit(limit).offset(offset)
        )
        sessions = result.scalars().all()

        return sessions
    except Exception as e:
        print(e)
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/complaints", response_model=schemas.VisitResponse, status_code=status.HTTP_201_CREATED)
async def create_visit_and_complaint(
    payload: schemas.ComplaintCreate,
    current_student: schemas.StudentResponse = Depends(oauth2.get_current_user),
    db: AsyncSession = Depends(database.get_db)
):
    try:
        # 1. Check that schedule exists and is available
        result = await db.execute(
            select(models.AppointmentSchedule)
            .options(joinedload(models.AppointmentSchedule.doctor))  # Eagerly load doctor
            .filter(
                models.AppointmentSchedule.schedule_id == payload.schedule_id,
                models.AppointmentSchedule.status == models.AppointmentStatus.available
            )
        )
        schedule = result.scalar_one_or_none()
        if not schedule:
            raise HTTPException(status_code=404, detail="Schedule not available")

        # 2. Prevent double-booking by the same student for the same slot
        result = await db.execute(
            select(models.ClinicVisit).filter(
                models.ClinicVisit.schedule_id == payload.schedule_id,
                models.ClinicVisit.student_id == current_student.student_id
            )
        )
        existing_visit = result.scalar_one_or_none()
        if existing_visit:
            raise HTTPException(status_code=400, detail="You already booked this slot")

        # 3. Create clinic visit
        visit = models.ClinicVisit(
            schedule_id=schedule.schedule_id,
            doctor_id=schedule.doctor_id,
            student_id=current_student.student_id,
            visit_date=schedule.date,
            status=models.VisitStatus.pending
        )
        db.add(visit)
        await db.flush()

        # 4. Add student complaint
        complaint = models.StudentComplaint(
            visit_id=visit.visit_id,
            student_id=current_student.student_id,
            complaint_description=payload.complaint_description
        )
        db.add(complaint)

        # 5. Update schedule status
        schedule.student_id = current_student.student_id
        schedule.status = models.AppointmentStatus.booked

        await db.commit()
        await db.refresh(visit)

        return {
            "visit_id": visit.visit_id,
            "schedule_id": schedule.schedule_id,
            "doctor_id": schedule.doctor_id,
            "doctor_name": schedule.doctor.username,
            "student_id": current_student.student_id,
            "visit_date": visit.visit_date,
            "status": visit.status,
            "created_at": visit.created_at,
            "complaint_description": complaint.complaint_description
        }
    except Exception as e:
        print(f"Visit creation error: {e}")
        raise HTTPException(status_code=500, detail="Internal error while creating visit")


@router.get("/me/all-visits", response_model=list[schemas.VisitResponse])  # Changed to VisitResponse
async def get_my_visits(
        current_student: schemas.StudentResponse = Depends(oauth2.get_current_user),
        db: AsyncSession = Depends(database.get_db)
):
    try:
        result = await db.execute(
            select(models.ClinicVisit)
            .options(
                joinedload(models.ClinicVisit.doctor),
                joinedload(models.ClinicVisit.complaints),
                joinedload(models.ClinicVisit.schedule)  # Added to load schedule
            )
            .filter(models.ClinicVisit.student_id == current_student.student_id)
            .order_by(models.ClinicVisit.created_at.desc())
        )
        visits = result.unique().scalars().all()  # Added unique() to handle joinedload

        if not visits:
            print(f"No visits found for student_id: {current_student.student_id}")
            return []

        response = [
            {
                "visit_id": visit.visit_id,
                "schedule_id": visit.schedule.schedule_id if visit.schedule else None,
                "doctor_id": visit.doctor_id,
                "doctor_name": visit.doctor.username if visit.doctor else "Unknown",
                "student_id": current_student.student_id,
                "visit_date": visit.visit_date,
                "status": visit.status,
                "created_at": visit.created_at,
                "complaint_description": visit.complaints[0].complaint_description if visit.complaints else None
            }
            for visit in visits
        ]
        # print(f"Fetched {len(response)} visits: {response[:2]}")
        return response
    except Exception as e:
        print(f"Error fetching visits: {e}")
        raise HTTPException(status_code=500, detail="Internal error while fetching visits")


@router.get("/me/visits/{visit_id}", response_model=schemas.VisitDetailedResponse)
async def get_visit_detail(
        visit_id: int,
        current_student: schemas.StudentResponse = Depends(oauth2.get_current_user),
        db: AsyncSession = Depends(database.get_db)
):
    try:
        # Step 1: Fetch visit with all related data
        result = await db.execute(
            select(models.ClinicVisit)
            .filter(
                models.ClinicVisit.visit_id == visit_id,
                models.ClinicVisit.student_id == current_student.student_id
            )
            .options(
                selectinload(models.ClinicVisit.complaints),
                selectinload(models.ClinicVisit.diagnoses)
                .selectinload(models.DoctorDiagnosis.prescriptions)
                .selectinload(models.DoctorPrescription.drug),
                selectinload(models.ClinicVisit.diagnoses)
                .selectinload(models.DoctorDiagnosis.complaints),
                selectinload(models.ClinicVisit.doctor),
                selectinload(models.ClinicVisit.schedule),
                selectinload(models.ClinicVisit.diagnoses)
                .selectinload(models.DoctorDiagnosis.prescriptions)
                .selectinload(models.DoctorPrescription.dispensations)
                .selectinload(models.DrugDispensation.drugs_given)
                .selectinload(models.DispensedDrugs.drug),
                selectinload(models.ClinicVisit.diagnoses)
                .selectinload(models.DoctorDiagnosis.prescriptions)
                .selectinload(models.DoctorPrescription.dispensations)
                .selectinload(models.DrugDispensation.pharmacist)
            )
        )
        visit = result.scalar_one_or_none()

        if not visit:
            raise HTTPException(status_code=404, detail="Visit not found")

        # Step 2: Extract values with proper null checks
        complaint = visit.complaints[0] if visit.complaints else None
        diagnosis = visit.diagnoses[0] if visit.diagnoses else None

        # Process prescriptions with dispensation data
        prescriptions_list = []
        if diagnosis:
            for prescription in diagnosis.prescriptions:
                dispensation_data = []
                for dispensation in prescription.dispensations:
                    drugs_given = []
                    for drug_given in dispensation.drugs_given:
                        drugs_given.append(schemas.DrugGivenView(
                            drug_name=drug_given.drug.name if drug_given.drug else None,
                            quantity=drug_given.quantity,
                            dispense_date=drug_given.dispense_date
                        ))

                    dispensation_data.append(schemas.DispensationView(
                        pharmacist_name=dispensation.pharmacist.username if dispensation.pharmacist else None,
                        dispensation_date=dispensation.created_at,
                        drugs_given=drugs_given
                    ))

                prescriptions_list.append(schemas.PrescriptionView(
                    drug_name=prescription.drug.name if prescription.drug else None,
                    dosage=prescription.dosage,
                    instructions=prescription.instructions,
                    dispensations=dispensation_data
                ))

        return schemas.VisitDetailedResponse(
            visit_id=visit.visit_id,
            schedule_id=visit.schedule.schedule_id if visit.schedule else None,
            doctor_id=visit.doctor_id,
            doctor_name=visit.doctor.username if visit.doctor else None,
            visit_date=visit.visit_date,
            status=visit.status,
            created_at=visit.created_at,
            complaint=schemas.ComplaintView(
                complaint_id=complaint.complaint_id if complaint else None,
                description=complaint.complaint_description if complaint else None,
                created_at=complaint.created_at if complaint else None
            ) if complaint else None,
            diagnosis=schemas.DiagnosisView(
                diagnosis_id=diagnosis.diagnosis_id if diagnosis else None,
                diagnosis_description=diagnosis.diagnosis_description if diagnosis else None,
                treatment_plan=diagnosis.treatment_plan if diagnosis else None,
                created_at=diagnosis.created_at if diagnosis else None
            ) if diagnosis else None,
            prescriptions=prescriptions_list
        )
    except Exception as e:
        print(f"Error fetching visit details: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")


@router.get("/schedules/available", response_model=list[schemas.AppointmentScheduledResponse])
async def get_student_available_schedules(
    db: AsyncSession = Depends(database.get_db)
):
    today = date.today()
    result = await db.execute(
        select(models.AppointmentSchedule)
        .filter(
            models.AppointmentSchedule.status == models.AppointmentStatus.available,
            models.AppointmentSchedule.date >= today
        )
        .order_by(models.AppointmentSchedule.date.asc(), models.AppointmentSchedule.start_time.asc())
        .options(selectinload(models.AppointmentSchedule.doctor))
    )
    schedules = result.scalars().all()

    # inject doctor_name dynamically if not already returned
    return [
        schemas.AppointmentScheduledResponse(
            schedule_id=s.schedule_id,
            doctor_id=s.doctor_id,
            doctor_name=s.doctor.username,
            student_id=s.student_id,
            availability_id=s.availability_id,
            date=s.date,
            start_time=s.start_time,
            end_time=s.end_time,
            status=s.status,
            created_at=s.created_at,
        )
        for s in schedules
    ]


@router.get("/students/me/dashboard", response_model=schemas.StudentDashboardResponse)
async def get_student_dashboard(
        current_student: schemas.StudentResponse = Depends(oauth2.get_current_user),
        db: AsyncSession = Depends(database.get_db)
):
    try:
        # Total visits count
        total_visits = await db.scalar(
            select(func.count(models.ClinicVisit.visit_id))
            .filter(models.ClinicVisit.student_id == current_student.student_id)
        )

        # Pending visits count
        pending_visits = await db.scalar(
            select(func.count(models.ClinicVisit.visit_id))
            .filter(
                models.ClinicVisit.student_id == current_student.student_id,
                models.ClinicVisit.status == models.VisitStatus.pending
            )
        )

        # Active doctors list
        doctors_result = await db.execute(
            select(models.User)
            .filter(
                models.User.role == models.UserRole.doctor,
                models.User.status == models.UserStatus.active
            )
            .order_by(models.User.username)
        )
        doctors = doctors_result.scalars().all()

        return {
            "total_visits": total_visits or 0,
            "pending_visits": pending_visits or 0,
            "active_doctors": [
                {
                    "doctor_id": doctor.user_id,
                    "name": doctor.username,
                    "email": doctor.email,
                    "phone": doctor.phone
                } for doctor in doctors
            ]
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))




