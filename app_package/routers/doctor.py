from fastapi import APIRouter, Depends, status, HTTPException, Request, Path
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from datetime import datetime
from typing import List

from sqlalchemy.orm import selectinload, joinedload

from .. import models, schemas, database, oauth2

router = APIRouter(
    prefix="/doctor",
    tags=["Doctor"]
)

# Dependency to ensure only doctors can access
async def get_current_doctor(
    current_user: schemas.TokenData = Depends(oauth2.get_current_user)
):
    if current_user.role != "doctor":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorized to perform this action"
        )
    return current_user


# 1
@router.post("/availabilities", response_model=schemas.AvailabilityResponse)
async def create_availability(
    availability: schemas.AvailabilityCreate,
    current_user: schemas.TokenData = Depends(get_current_doctor),
    db: AsyncSession = Depends(database.get_db),
    request: Request = None
):
    # Validate time range
    if availability.start_time >= availability.end_time:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Start time must be before end time"
        )

    # Check for overlapping availability
    result = await db.execute(
        select(models.Availability).filter(
            models.Availability.doctor_id == current_user.user_id,
            models.Availability.day_of_week == availability.day_of_week,
            models.Availability.start_time < availability.end_time,
            models.Availability.end_time > availability.start_time
        )
    )
    if result.scalar_one_or_none():
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Availability overlaps with existing slot"
        )

    db_availability = models.Availability(
        doctor_id=current_user.user_id,
        day_of_week=availability.day_of_week,
        start_time=availability.start_time,
        end_time=availability.end_time,
        status=availability.status
    )
    db.add(db_availability)
    await db.commit()
    await db.refresh(db_availability)
    # await log_access(db, current_user.user_id, None, "create_availability", request.client.host)
    return db_availability

# 2
@router.get("/availabilities", response_model=List[schemas.AvailabilityResponse])
async def get_availabilities(
    current_user: schemas.TokenData = Depends(get_current_doctor),
    db: AsyncSession = Depends(database.get_db),
    request: Request = None
):
    result = await db.execute(
        select(models.Availability).filter(
            models.Availability.doctor_id == current_user.user_id
        )
    )
    availabilities = result.scalars().all()
    # await log_access(db, current_user.user_id, None, "list_availabilities", request.client.host)
    return availabilities


# 3
@router.put("/availability/{availability_id}", response_model=schemas.AvailabilityResponse)
async def update_availability(
    availability_id: int,
    availability_update: schemas.AvailabilityUpdate,
    current_user: schemas.TokenData = Depends(get_current_doctor),
    db: AsyncSession = Depends(database.get_db),
    request: Request = None
):
    async with db.begin():
        result = await db.execute(
            select(models.Availability).filter(
                models.Availability.availability_id == availability_id,
                models.Availability.doctor_id == current_user.user_id
            )
        )
        availability = result.scalar_one_or_none()

        if not availability:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Availability not found")

        update_data = availability_update.dict(exclude_unset=True)
        for key, value in update_data.items():
            setattr(availability, key, value)

        await db.commit()
        await db.refresh(availability)

    # await log_access(db, current_user.user_id, None, f"update_availability_{availability_id}", request.client.host)
    return availability


# 4
@router.delete("/availability/{availability_id}", response_model=schemas.MessageResponse)
async def delete_availability(
    availability_id: int,
    current_user: schemas.TokenData = Depends(get_current_doctor),
    db: AsyncSession = Depends(database.get_db),
    request: Request = None
):
    async with db.begin():
        result = await db.execute(
            select(models.Availability).filter(
                models.Availability.availability_id == availability_id,
                models.Availability.doctor_id == current_user.user_id
            )
        )
        availability = result.scalar_one_or_none()

        if not availability:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Availability not found")

        await db.delete(availability)
        await db.commit()

    # await log_access(db, current_user.user_id, None, f"delete_availability_{availability_id}", request.client.host)
    return {"detail": "Availability deleted"}


# 5
@router.post("/schedules", response_model=schemas.AppointmentScheduleResponse)
async def create_schedule(
        schedule: schemas.AppointmentScheduleCreate,
        current_user: schemas.TokenData = Depends(get_current_doctor),
        db: AsyncSession = Depends(database.get_db),
        request: Request = None
):
    # Validate time range
    if schedule.start_time >= schedule.end_time:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Start time must be before end time"
        )

    try:
        # Verify availability exists and belongs to the doctor
        availability = await db.execute(
            select(models.Availability).filter(
                models.Availability.availability_id == schedule.availability_id,
                models.Availability.doctor_id == current_user.user_id,
                models.Availability.status == models.AvailabilityStatus.active
            )
        )
        availability = availability.scalar_one_or_none()

        if not availability:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Availability not found or not active"
            )
        print(schedule)
        # Check if date matches availability's day of week
        weekday_names = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]
        schedule_day_name = weekday_names[schedule.date.weekday()]

        if schedule_day_name != availability.day_of_week.value:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Schedule date doesn't match availability day of week"
            )

        # Check if time falls within availability hours
        if (schedule.start_time < availability.start_time or
                schedule.end_time > availability.end_time):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Schedule time must fall within availability hours"
            )

        # Check for overlapping schedules
        existing_schedule = await db.execute(
            select(models.AppointmentSchedule).filter(
                models.AppointmentSchedule.doctor_id == current_user.user_id,
                models.AppointmentSchedule.date == schedule.date,
                models.AppointmentSchedule.start_time < schedule.end_time,
                models.AppointmentSchedule.end_time > schedule.start_time
            )
        )
        if existing_schedule.scalar_one_or_none():
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Schedule overlaps with existing slot"
            )

        db_schedule = models.AppointmentSchedule(
            doctor_id=current_user.user_id,
            availability_id=schedule.availability_id,
            date=schedule.date,
            start_time=schedule.start_time,
            end_time=schedule.end_time,
            status=models.AppointmentStatus.available
        )
        db.add(db_schedule)
        await db.commit()
        await db.refresh(db_schedule)

        # await log_access(db, current_user.user_id, None, "create_schedule", request.client.host)
        return db_schedule

    except HTTPException:
        raise
    except Exception as e:
        print(e)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to create schedule"
        )

# 6
@router.put("/schedules/{schedule_id}", response_model=schemas.AppointmentScheduleResponse)
async def update_schedule(
    schedule_id: int,
    schedule_update: schemas.AppointmentScheduleUpdate,
    current_user: schemas.TokenData = Depends(get_current_doctor),
    db: AsyncSession = Depends(database.get_db),
    request: Request = None
):

    result = await db.execute(
        select(models.AppointmentSchedule).filter(
            models.AppointmentSchedule.schedule_id == schedule_id,
            models.AppointmentSchedule.doctor_id == current_user.user_id
        )
    )
    schedule = result.scalar_one_or_none()

    if not schedule:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Availability not found")

    update_data = schedule_update.dict(exclude_unset=True)
    for key, value in update_data.items():
        setattr(schedule, key, value)

    await db.commit()
    await db.refresh(schedule)

    # await log_access(db, current_user.user_id, None, f"update_availability_{schedule_id}", request.client.host)
    return schedule

# 7
@router.post("/visits", response_model=schemas.ClinicVisitResponse)
async def create_visit(
    visit: schemas.ClinicVisitCreate,
    current_user: schemas.TokenData = Depends(get_current_doctor),
    db: AsyncSession = Depends(database.get_db),
    request: Request = None
):
    # Verify student exists
    result = await db.execute(
        select(models.Student).filter(models.Student.student_id == visit.student_id)
    )
    student = result.scalar_one_or_none()
    if not student:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Student not found"
        )

    # Verify schedule (if provided)
    if visit.schedule_id:
        result = await db.execute(
            select(models.AppointmentSchedule).filter(
                models.AppointmentSchedule.schedule_id == visit.schedule_id,
                models.AppointmentSchedule.doctor_id == current_user.user_id
            )
        )
        schedule = result.scalar_one_or_none()
        if not schedule:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Schedule not found or not assigned to this doctor"
            )

    db_visit = models.ClinicVisit(
        student_id=visit.student_id,
        doctor_id=current_user.user_id,
        schedule_id=visit.schedule_id,
        visit_date=visit.visit_date,
        status=visit.status
    )
    db.add(db_visit)
    await db.commit()
    await db.refresh(db_visit)
    return db_visit

# 8
@router.post("/diagnoses", response_model=schemas.DiagnosisResponse)
async def create_diagnosis(
        diagnosis: schemas.DiagnosisCreate,
        current_user: schemas.TokenData = Depends(get_current_doctor),
        db: AsyncSession = Depends(database.get_db),
        request: Request = None
):
    # Verify visit exists and belongs to this doctor
    result = await db.execute(
        select(models.ClinicVisit).filter(
            models.ClinicVisit.visit_id == diagnosis.visit_id,
            models.ClinicVisit.doctor_id == current_user.user_id
        )
    )
    visit = result.scalar_one_or_none()
    if not visit:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Visit not found or not assigned to this doctor"
        )

    # Verify student matches visit
    if visit.student_id != diagnosis.student_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Student ID does not match visit"
        )

    db_diagnosis = models.DoctorDiagnosis(
        visit_id=diagnosis.visit_id,
        student_id=diagnosis.student_id,
        complaint_id=diagnosis.complaint_id,
        doctor_id=current_user.user_id,
        diagnosis_description=diagnosis.diagnosis_description,
        treatment_plan=diagnosis.treatment_plan
    )
    db.add(db_diagnosis)

    try:
        await db.commit()
        await db.refresh(db_diagnosis)

        # After successful commit, check if visit has a schedule_id and update status
        if visit.schedule_id:
            result = await db.execute(
                select(models.AppointmentSchedule)
                .filter(models.AppointmentSchedule.schedule_id == visit.schedule_id)
            )
            schedule = result.scalar_one_or_none()
            if schedule:
                schedule.status = schemas.AppointmentStatus.completed
                await db.commit()

        return db_diagnosis

    except Exception as e:
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error creating diagnosis: {str(e)}"
        )



# 9
@router.post("/prescriptions", response_model=schemas.PrescriptionResponse)
async def create_prescription(
    prescription: schemas.PrescriptionCreate,
    current_user: schemas.TokenData = Depends(get_current_doctor),
    db: AsyncSession = Depends(database.get_db),
    request: Request = None
):
    # Verify diagnosis exists and belongs to this doctor
    result = await db.execute(
        select(models.DoctorDiagnosis).filter(
            models.DoctorDiagnosis.diagnosis_id == prescription.diagnosis_id,
            models.DoctorDiagnosis.doctor_id == current_user.user_id
        )
    )
    diagnosis = result.scalar_one_or_none()
    if not diagnosis:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Diagnosis not found or not assigned to this doctor"
        )

    # Verify student matches diagnosis
    if diagnosis.student_id != prescription.student_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Student ID does not match diagnosis"
        )

    # Verify drug exists
    result = await db.execute(
        select(models.Drugs).filter(models.Drugs.drug_id == prescription.drug_id)
    )
    drug = result.scalar_one_or_none()
    if not drug:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Drug not found"
        )

    db_prescription = models.DoctorPrescription(
        diagnosis_id=prescription.diagnosis_id,
        student_id=prescription.student_id,
        doctor_id=current_user.user_id,
        drug_id=prescription.drug_id,
        dosage=prescription.dosage,
        instructions=prescription.instructions
    )
    db.add(db_prescription)
    await db.commit()
    await db.refresh(db_prescription)
    # await log_access(db, current_user.user_id, prescription.student_id, "create_prescription", request.client.host)
    return db_prescription


# 10
@router.post("/complaints", response_model=schemas.ComplaintResponse)
async def review_complaint(
    complaint: schemas.ComplaintCreate,
    current_user: schemas.TokenData = Depends(get_current_doctor),
    db: AsyncSession = Depends(database.get_db),
    request: Request = None
):
    # Verify visit exists and belongs to this doctor
    result = await db.execute(
        select(models.ClinicVisit).filter(
            models.ClinicVisit.visit_id == complaint.visit_id,
            models.ClinicVisit.doctor_id == current_user.user_id
        )
    )
    visit = result.scalar_one_or_none()
    if not visit:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Visit not found or not assigned to this doctor"
        )

    # Verify student matches visit
    if visit.student_id != complaint.student_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Student ID does not match visit"
        )

    db_complaint = models.StudentComplaint(
        visit_id=complaint.visit_id,
        student_id=complaint.student_id,
        doctor_id=current_user.user_id,
        complaint_description=complaint.complaint_description
    )
    db.add(db_complaint)
    await db.commit()
    await db.refresh(db_complaint)
    # await log_access(db, current_user.user_id, complaint.student_id, "review_complaint", request.client.host)
    return db_complaint


# 11
@router.get("/schedules", response_model=List[schemas.AppointmentScheduleResponse])
async def get_doctor_schedules(
        current_user: schemas.TokenData = Depends(get_current_doctor),
        db: AsyncSession = Depends(database.get_db),
        request: Request = None
):
    try:
        stmt = (
            select(
                models.AppointmentSchedule,
                models.Availability.day_of_week
            )
            .join(
                models.Availability,
                models.AppointmentSchedule.availability_id == models.Availability.availability_id
            )
            .filter(models.AppointmentSchedule.doctor_id == current_user.user_id)   # "UIL/25/025"
            .order_by(models.AppointmentSchedule.date, models.AppointmentSchedule.start_time)
        )

        result = await db.execute(stmt)

        return [
            {
                "schedule_id": schedule.schedule_id,
                "doctor_id": schedule.doctor_id,
                "student_id": schedule.student_id,
                "availability_id": schedule.availability_id,
                "start_time": schedule.start_time,
                "end_time": schedule.end_time,
                "date": schedule.date,
                "status": schedule.status,
                "created_at": schedule.created_at,
                "day_of_week": day_of_week
            }
            for schedule, day_of_week in result.all()
        ]

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error fetching schedules: {str(e)}"
        )


@router.put("/schedules/{schedule_id}/cancel", response_model=schemas.AppointmentScheduleResponse)
async def cancel_schedule(
    schedule_id: int = Path(..., description="The ID of the schedule to cancel"),
    current_user: schemas.TokenData = Depends(get_current_doctor),
    db: AsyncSession = Depends(database.get_db),
    request: Request = None
):
    # Fetch the schedule
    result = await db.execute(
        select(models.AppointmentSchedule).where(models.AppointmentSchedule.schedule_id == schedule_id)
    )
    schedule = result.scalar_one_or_none()

    if not schedule:
        raise HTTPException(status_code=404, detail="Schedule not found")

    if schedule.doctor_id != current_user.user_id:
        raise HTTPException(status_code=403, detail="Not authorized to cancel this schedule")

    # Check if already cancelled
    if schedule.status == models.AppointmentStatus.cancelled:
        raise HTTPException(status_code=400, detail="Schedule is already cancelled")

    # Update status
    schedule.status = models.AppointmentStatus.cancelled
    await db.commit()
    await db.refresh(schedule)

    # Log access
    # await log_access(db, current_user.user_id, schedule_id, "cancel_schedule", request.client.host)

    return schedule


# ====================================================================================================================
@router.get("/doctor/visits/{visit_id}/details", response_model=schemas.VisitDetailResponse)
async def get_visit_details(
        visit_id: int,
        # current_user: schemas.TokenData = Depends(get_current_doctor),
        db: AsyncSession = Depends(database.get_db),
        request: Request = None
):
    # First query the visit with all necessary relationships
    result = await db.execute(
        select(models.ClinicVisit)
        .options(
            selectinload(models.ClinicVisit.student)
            .selectinload(models.Student.faculty),
            selectinload(models.ClinicVisit.student)
            .selectinload(models.Student.department),
            selectinload(models.ClinicVisit.student)
            .selectinload(models.Student.level),
            selectinload(models.ClinicVisit.complaints),
            selectinload(models.ClinicVisit.diagnoses)
            .selectinload(models.DoctorDiagnosis.prescriptions)
            .selectinload(models.DoctorPrescription.drug)
        )
        .filter(models.ClinicVisit.visit_id == visit_id)
    )
    visit = result.scalar_one_or_none()

    if not visit:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Visit not found")

    complaint = None
    if visit.complaints:
        complaint = schemas.ComplaintOut(
                complaint_description=visit.complaints[0].complaint_description,
                created_at=visit.complaints[0].created_at
            )

    # Prepare the diagnosis data if exists
    diagnosis = None
    if visit.diagnoses:
        diagnosis_data = visit.diagnoses[0]
        prescriptions = [
            schemas.PrescriptionOut(
                prescription_id=p.prescription_id,
                drug_id=p.drug_id,
                drug_name=p.drug.name,
                dosage=p.dosage,
                instructions=p.instructions
            )
            for p in diagnosis_data.prescriptions
        ]

        diagnosis = schemas.DiagnosisOut(
            diagnosis_id=diagnosis_data.diagnosis_id,
            diagnosis_description=diagnosis_data.diagnosis_description,
            treatment_plan=diagnosis_data.treatment_plan,
            prescriptions=prescriptions
        )

    return schemas.VisitDetailResponse(
        visit_id=visit.visit_id,
        visit_date=visit.visit_date,
        status=visit.status,
        student=schemas.StudentInfoOut(
            student_id=visit.student.student_id,
            full_name=f"{visit.student.first_name} {visit.student.surname}",
            matric_number=visit.student.matriculation_number,
            gender=visit.student.gender,
            faculty=visit.student.faculty.faculty_name,
            department=visit.student.department.department_name,
            level=visit.student.level.level_name
        ),
        complaints=complaint,
        diagnosis=diagnosis
    )


@router.get("/doctors/me/get-doctors-dashboard", response_model=schemas.DoctorDashboardResponse)
async def get_doctor_dashboard(
    current_doctor: schemas.TokenData = Depends(get_current_doctor),
    db: AsyncSession = Depends(database.get_db)
):
    try:
        # Pending visits with explicit student loading
        pending_stmt = (
            select(models.ClinicVisit)
            .join(models.Student)
            .options(joinedload(models.ClinicVisit.student))
            .where(
                models.ClinicVisit.doctor_id == current_doctor.user_id,
                models.ClinicVisit.status == models.VisitStatus.pending
            )
            .order_by(models.ClinicVisit.visit_date)
        )
        pending_result = await db.execute(pending_stmt)
        pending_visits = pending_result.unique().scalars().all()

        # Completed visits count
        completed_stmt = (
            select(func.count(models.ClinicVisit.visit_id))
            .where(
                models.ClinicVisit.doctor_id == current_doctor.user_id,
                models.ClinicVisit.status == models.VisitStatus.completed
            )
        )
        completed_visits = (await db.execute(completed_stmt)).scalar_one()

        # Upcoming appointments with explicit student loading
        appointments_stmt = (
            select(models.AppointmentSchedule)
            .join(models.Student)
            .options(joinedload(models.AppointmentSchedule.student))
            .where(
                models.AppointmentSchedule.doctor_id == current_doctor.user_id,
                models.AppointmentSchedule.status == models.AppointmentStatus.booked,
                models.AppointmentSchedule.date >= func.current_date()
            )
            .order_by(models.AppointmentSchedule.date, models.AppointmentSchedule.start_time)
            .limit(5)
        )
        appointments_result = await db.execute(appointments_stmt)
        appointments = appointments_result.unique().scalars().all()

        return {
            "pending_visits": [
                {
                    "visit_id": visit.visit_id,
                    "student_name": f"{visit.student.first_name} {visit.student.surname}",
                    "visit_date": visit.visit_date,
                    "matric_number": visit.student.matriculation_number
                } for visit in pending_visits
            ],
            "total_completed_visits": completed_visits or 0,
            "upcoming_appointments": [
                {
                    "schedule_id": appt.schedule_id,
                    "student_name": f"{appt.student.first_name} {appt.student.surname}",
                    "date": appt.date,
                    "time": f"{appt.start_time.strftime('%H:%M')} - {appt.end_time.strftime('%H:%M')}",
                    "matric_number": appt.student.matriculation_number
                } for appt in appointments if appt.student
            ]
        }

    except Exception as e:
        # No need to manually rollback - FastAPI will handle it
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error fetching doctor dashboard: {str(e)}"
        )


@router.get("/doctor/visits", response_model=List[schemas.DoctorPendingVisitResponse])
async def get_doctor_pending_visits(
        current_doctor: schemas.TokenData = Depends(get_current_doctor),
        db: AsyncSession = Depends(database.get_db)
):
    """
    Returns all pending visits booked for the current doctor with student details and complaints.
    """
    try:
        result = await db.execute(
            select(
                models.ClinicVisit.visit_id,
                models.Student.first_name,
                models.Student.surname,
                models.Student.matriculation_number,
                models.Student.student_id,
                models.ClinicVisit.visit_date,
                models.AppointmentSchedule.start_time,
                models.AppointmentSchedule.end_time,
                models.StudentComplaint.complaint_id,
                models.StudentComplaint.complaint_description,
                models.ClinicVisit.schedule_id
            )
            .join(models.Student, models.ClinicVisit.student_id == models.Student.student_id)
            .join(models.StudentComplaint, models.ClinicVisit.visit_id == models.StudentComplaint.visit_id)
            .outerjoin(models.AppointmentSchedule,
                       models.ClinicVisit.schedule_id == models.AppointmentSchedule.schedule_id)
            .where(
                models.ClinicVisit.doctor_id == current_doctor.user_id,
                models.ClinicVisit.status == models.VisitStatus.pending
            )
            .order_by(models.ClinicVisit.visit_date)
        )

        visits = result.all()

        return [
            {
                "visit_id": visit.visit_id,
                "student_id": visit.student_id,
                "student_name": f"{visit.first_name} {visit.surname}",
                "matric_number": visit.matriculation_number,
                "visit_date": visit.visit_date,
                "time_slot": f"{visit.start_time.strftime('%H:%M')} - {visit.end_time.strftime('%H:%M')}" if visit.start_time else "Not scheduled",
                "complaint_id": visit.complaint_id,
                "complaint_description": visit.complaint_description,
                "schedule_id": visit.schedule_id
            }
            for visit in visits
        ]

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error fetching pending visits: {str(e)}"
        )

# =========================================================================================================

# 1. Route to fetch diagnoses by visit ID
@router.get("/visits/{visit_id}/diagnoses", response_model=List[schemas.DiagnosisResponse])
async def get_diagnoses_by_visit(
        visit_id: int,
        current_user: schemas.TokenData = Depends(get_current_doctor),
        db: AsyncSession = Depends(database.get_db)
):
    # Verify visit exists and belongs to this doctor
    result = await db.execute(
        select(models.ClinicVisit).filter(
            models.ClinicVisit.visit_id == visit_id,
            models.ClinicVisit.doctor_id == current_user.user_id
        )
    )
    visit = result.scalar_one_or_none()
    if not visit:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Visit not found or not assigned to this doctor"
        )

    # Get all diagnoses for this visit
    result = await db.execute(select(models.DoctorDiagnosis).filter(models.DoctorDiagnosis.visit_id == visit_id))
    diagnoses = result.scalars().all()
    return diagnoses


# 2. Route to create prescriptions (handles single or multiple)
@router.post("/prescriptions", response_model=List[schemas.PrescriptionResponse])
async def create_prescriptions(
        prescriptions: List[schemas.PrescriptionCreate],
        current_user: schemas.TokenData = Depends(get_current_doctor),
        db: AsyncSession = Depends(database.get_db)
):
    created_prescriptions = []

    for prescription in prescriptions:
        # Verify diagnosis exists and belongs to this doctor
        result = await db.execute(
            select(models.DoctorDiagnosis).filter(
                models.DoctorDiagnosis.diagnosis_id == prescription.diagnosis_id,
                models.DoctorDiagnosis.doctor_id == current_user.user_id
            )
        )
        diagnosis = result.scalar_one_or_none()
        if not diagnosis:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Diagnosis with ID {prescription.diagnosis_id} not found or not created by this doctor"
            )

        # Verify drug exists
        result = await db.execute(
            select(models.Drugs).filter(models.Drugs.drug_id == prescription.drug_id)
        )
        drug = result.scalar_one_or_none()
        if not drug:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Drug with ID {prescription.drug_id} not found"
            )

        # Create prescription
        db_prescription = models.DoctorPrescription(
            diagnosis_id=prescription.diagnosis_id,
            student_id=prescription.student_id,
            doctor_id=current_user.user_id,
            drug_id=prescription.drug_id,
            dosage=prescription.dosage,
            instructions=prescription.instructions
        )
        db.add(db_prescription)
        created_prescriptions.append(db_prescription)

    await db.commit()

    # Refresh all created prescriptions to get their IDs
    for prescription in created_prescriptions:
        await db.refresh(prescription)

    return created_prescriptions


# 3. Route to fetch prescriptions by visit ID
@router.get("/visits/{visit_id}/prescriptions", response_model=List[schemas.PrescriptionResponse])
async def get_prescriptions_by_visit(
        visit_id: int,
        current_user: schemas.TokenData = Depends(get_current_doctor),
        db: AsyncSession = Depends(database.get_db)
):
    # Verify visit exists and belongs to this doctor
    result = await db.execute(
        select(models.ClinicVisit).filter(
            models.ClinicVisit.visit_id == visit_id,
            models.ClinicVisit.doctor_id == current_user.user_id
        )
    )
    visit = result.scalar_one_or_none()
    if not visit:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Visit not found or not assigned to this doctor"
        )

    # Get all prescriptions for this visit through diagnoses
    result = await db.execute(
        select(models.DoctorPrescription)
        .join(models.DoctorDiagnosis)
        .filter(models.DoctorDiagnosis.visit_id == visit_id)
    )
    prescriptions = result.scalars().all()
    return prescriptions

# 4. Route to mark appointment as completed
@router.post("/visits/{visit_id}/complete", response_model=schemas.VisitResponse)
async def complete_visit(
    visit_id: int,
    current_user: schemas.TokenData = Depends(get_current_doctor),
    db: AsyncSession = Depends(database.get_db)
):
    # Verify visit exists and belongs to this doctor
    result = await db.execute(
        select(models.ClinicVisit).filter(
            models.ClinicVisit.visit_id == visit_id,
            models.ClinicVisit.doctor_id == current_user.user_id,
            models.ClinicVisit.status == schemas.VisitStatus.pending
        )
    )
    visit = result.scalar_one_or_none()
    if not visit:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Visit not found, not assigned to this doctor, or not pending"
        )

    # Update visit status to completed
    visit.status = schemas.VisitStatus.completed
    await db.commit()
    await db.refresh(visit)

    # If this was a scheduled appointment, update the schedule status
    if visit.schedule_id:
        result = await db.execute(
            select(models.AppointmentSchedule)
            .filter(models.AppointmentSchedule.schedule_id == visit.schedule_id)
        )
        schedule = result.scalar_one_or_none()
        if schedule:
            schedule.status = schemas.AppointmentStatus.completed
            await db.commit()

    return visit


@router.post("/create-multi-prescriptions", response_model=List[schemas.PrescriptionResponse])
async def create_prescriptions(
        prescriptions: List[schemas.PrescriptionCreate],
        current_user: schemas.TokenData = Depends(get_current_doctor),
        db: AsyncSession = Depends(database.get_db)
):
    created_prescriptions = []

    for prescription in prescriptions:
        # Verify diagnosis exists and belongs to this doctor
        result = await db.execute(
            select(models.DoctorDiagnosis).filter(
                models.DoctorDiagnosis.diagnosis_id == prescription.diagnosis_id,
                models.DoctorDiagnosis.doctor_id == current_user.user_id
            )
        )
        diagnosis = result.scalar_one_or_none()
        if not diagnosis:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Diagnosis with ID {prescription.diagnosis_id} not found or not created by this doctor"
            )

        # Verify drug exists
        result = await db.execute(
            select(models.Drugs).filter(models.Drugs.drug_id == prescription.drug_id)
        )
        drug = result.scalar_one_or_none()
        if not drug:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Drug with ID {prescription.drug_id} not found"
            )

        # Create prescription
        db_prescription = models.DoctorPrescription(
            diagnosis_id=prescription.diagnosis_id,
            student_id=prescription.student_id,
            doctor_id=current_user.user_id,
            drug_id=prescription.drug_id,
            dosage=prescription.dosage,
            instructions=prescription.instructions
        )
        db.add(db_prescription)
        created_prescriptions.append(db_prescription)

    await db.commit()

    # Refresh all created prescriptions to get their IDs
    for prescription in created_prescriptions:
        await db.refresh(prescription)

    return created_prescriptions

