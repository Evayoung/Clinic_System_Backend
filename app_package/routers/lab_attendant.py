
from datetime import datetime
from fastapi import APIRouter, Depends, status, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from typing import List

from .. import models, schemas, database, oauth2

router = APIRouter(
    prefix="/lab",
    tags=["Lab Attendant"]
)


# 1. Create health record
@router.post("/create-records/", response_model=schemas.HealthRecordResponse)
async def create_health_record(
        record_data: schemas.HealthRecordCreate,
        db: AsyncSession = Depends(database.get_db),
        current_user: models.User = Depends(oauth2.get_current_user)
):
    # Verify user is a lab attendant
    if current_user.role.value != "lab_attendant":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only lab attendants can create health records"
        )

    # Get student by matric number
    result = await db.execute(
        select(models.Student).where(models.Student.matriculation_number == record_data.matric_number)
    )
    student = result.scalars().first()

    if not student:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Student not found"
        )

    # Convert enum values to strings if needed
    blood_group = record_data.blood_group.value if record_data.blood_group else None
    genotype = record_data.genotype.value if record_data.genotype else None

    # Create new health record
    new_record = models.HealthRecord(
        student_id=student.student_id,
        blood_group=blood_group,  # Use the string value
        genotype=genotype,  # Use the string value
        height=record_data.height,
        weight=record_data.weight,
        test_date=record_data.test_date,
        lab_attendant_id=current_user.user_id,
        notes=record_data.notes
    )

    db.add(new_record)
    await db.commit()
    await db.refresh(new_record)

    # Get department name
    result = await db.execute(
        select(models.Department.department_name)
        .where(models.Department.department_id == student.department_id)
    )
    department_name = result.scalars().first()

    return {
        "student_name": f"{student.surname} {student.first_name}",
        "matric_number": student.matriculation_number,
        "department": department_name,
        "blood_group": new_record.blood_group,
        "genotype": new_record.genotype,
        "height": new_record.height,
        "weight": new_record.weight,
        "test_date": new_record.test_date,
        "notes": new_record.notes,
        "created_at": new_record.created_at,
        "updated_at": new_record.updated_at
    }

# 2. Update health record by matric number
@router.put("/update-records", response_model=schemas.HealthRecordResponse, status_code=status.HTTP_200_OK)
async def update_health_record(
        matric_number: str,
        record_data: schemas.HealthRecordUpdate,
        db: AsyncSession = Depends(database.get_db),
        current_user: models.User = Depends(oauth2.get_current_user)
):
    # Verify user is a lab attendant
    if current_user.role.value != "lab_attendant":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only lab attendants can create health records"
        )

    # Get student by matric number
    result = await db.execute(select(models.Student).where(models.Student.matriculation_number == matric_number))
    student = result.scalars().first()

    if not student:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Student not found"
        )

    # Get the latest health record for the student
    result = await db.execute(
        select(models.HealthRecord)
        .where(models.HealthRecord.student_id == student.student_id)
        .order_by(models.HealthRecord.created_at.desc())
    )
    health_record = result.scalars().first()

    if not health_record:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No health record found for this student"
        )

    # Update the record
    if record_data.blood_group is not None:
        health_record.blood_group = record_data.blood_group
    if record_data.genotype is not None:
        health_record.genotype = record_data.genotype
    if record_data.height is not None:
        health_record.height = record_data.height
    if record_data.weight is not None:
        health_record.weight = record_data.weight
    if record_data.test_date is not None:
        health_record.test_date = record_data.test_date
    if record_data.notes is not None:
        health_record.notes = record_data.notes

    health_record.lab_attendant_id = current_user.user_id

    await db.commit()
    await db.refresh(health_record)

    # Get department name
    result = await db.execute(
        select(models.Department.department_name)
        .where(models.Department.department_id == student.department_id)
    )
    department_name = result.scalars().first()

    return {
        "student_name": f"{student.surname} {student.first_name}",
        "matric_number": student.matriculation_number,
        "department": department_name,
        "blood_group": health_record.blood_group,
        "genotype": health_record.genotype,
        "height": health_record.height,
        "weight": health_record.weight,
        "test_date": health_record.test_date,
        "notes": health_record.notes,
        "created_at": health_record.created_at,
        "updated_at": health_record.updated_at
    }


# 3. Get all health records
@router.get("/get-all-records/", response_model=List[schemas.HealthRecordResponse])
async def get_all_health_records(
        db: AsyncSession = Depends(database.get_db),
        skip: int = 0,
        limit: int = 100
):


    # Get all health records with student and department info
    result = await db.execute(
        select(models.HealthRecord, models.Student, models.Department)
        .join(models.Student, models.HealthRecord.student_id == models.Student.student_id)
        .join(models.Department, models.Student.department_id == models.Department.department_id)
        .order_by(models.HealthRecord.created_at.desc())
        .offset(skip)
        .limit(limit)
    )
    records = result.all()

    response = []
    for record, student, department in records:
        response.append({
            "student_name": f"{student.surname} {student.first_name}",
            "matric_number": student.matriculation_number,
            "department": department.department_name,
            "blood_group": record.blood_group,
            "genotype": record.genotype,
            "height": record.height,
            "weight": record.weight,
            "test_date": record.test_date,
            "notes": record.notes,
            "created_at": record.created_at,
            "updated_at": record.updated_at
        })

    return response


# 4. Get health records by matric number
@router.get("/get-health-records", response_model=List[schemas.HealthRecordResponse1])
async def get_health_records_by_matric(
        matric_number: str,
        db: AsyncSession = Depends(database.get_db),
        current_user: models.User = Depends(oauth2.get_current_user)
):
    # Verify user is a lab attendant
    if current_user.role != models.UserRole.lab_attendant:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only lab attendants can view health records"
        )

    # Get student by matric number
    result = await db.execute(select(models.Student).where(models.Student.matriculation_number == matric_number))
    student = result.scalars().first()

    if not student:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Student not found"
        )

    # Get all health records for the student
    result = await db.execute(
        select(models.HealthRecord)
        .where(models.HealthRecord.student_id == student.student_id)
        .order_by(models.HealthRecord.created_at.desc())
    )
    records = result.scalars().all()

    return records