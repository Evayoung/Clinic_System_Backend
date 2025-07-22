from datetime import datetime

from fastapi import APIRouter, Depends, status, HTTPException, Request
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from typing import List

from .. import models, schemas, database, oauth2

router = APIRouter(
    prefix="/general",
    tags=["General"]
)

async def log_access(db: AsyncSession, user_id: str, student_id: int, action: str, ip_address: str):
    access_log = models.AccessLog(
        user_id=user_id,
        student_id=student_id,
        action=action,
        ip_address=ip_address,
        timestamp=datetime.utcnow()
    )
    db.add(access_log)
    await db.commit()

@router.get("/drugs", response_model=List[schemas.DrugResponse])
async def get_drugs(
    db: AsyncSession = Depends(database.get_db),
    request: Request = None
):
    result = await db.execute(
        select(models.Drugs)
    )
    drugs = result.scalars().all()

    await log_access(db, None, None, "list_drugs", request.client.host)
    return drugs

@router.get("/students/{student_id}", response_model=schemas.StudentResponse)
async def get_student(
    student_id: int,
    current_user: schemas.TokenData = Depends(oauth2.get_current_user),
    db: AsyncSession = Depends(database.get_db),
    request: Request = None
):
    if current_user.role not in ["admin", "doctor", "pharmacist", "lab_attendant"]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorized to view student details"
        )

    result = await db.execute(
        select(models.Student).filter(models.Student.student_id == student_id)
    )
    student = result.scalar_one_or_none()
    if not student:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Student not found"
        )

    await log_access(db, current_user.user_id, student_id, f"get_student_{student_id}", request.client.host)
    return student

@router.get("/available-schedules", response_model=List[schemas.AppointmentScheduleResponse])
async def get_available_schedules(
    db: AsyncSession = Depends(database.get_db),
    request: Request = None
):
    result = await db.execute(
        select(models.AppointmentSchedule)
        .filter(
            models.AppointmentSchedule.student_id.is_(None),
            models.AppointmentSchedule.status == models.AppointmentStatus.booked
        )
    )
    schedules = result.scalars().all()

    await log_access(db, None, None, "list_available_schedules", request.client.host)
    return schedules