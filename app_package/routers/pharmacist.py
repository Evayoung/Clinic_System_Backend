from fastapi import APIRouter, Depends, status, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update, func
from sqlalchemy.orm import joinedload
from typing import List

from .. import models, schemas, database, oauth2

router = APIRouter(
    prefix="/pharmacist",
    tags=["Pharmacist"]
)

async def get_current_pharmacist(
    current_user: schemas.TokenData = Depends(oauth2.get_current_user),
):
    if current_user.role != "pharmacist":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorized to perform this action"
        )
    return current_user

@router.get("/students/search", response_model=schemas.StudentWithRelationResponse)
async def search_student(
    matriculation_number: str,
    db: AsyncSession = Depends(database.get_db),
    current_user: schemas.TokenData = Depends(get_current_pharmacist)
):
    result = await db.execute(
        select(models.Student)
        .filter(models.Student.matriculation_number == matriculation_number)
        .options(
            joinedload(models.Student.faculty),
            joinedload(models.Student.department),
            joinedload(models.Student.level)
        )
    )
    student = result.scalars().first()
    if not student:
        raise HTTPException(status_code=404, detail="Student not found")
    return student

@router.get("/prescriptions", response_model=List[schemas.PrescriptionsResponse])
async def get_prescriptions(
    student_id: int,
    db: AsyncSession = Depends(database.get_db),
    current_user: schemas.TokenData = Depends(get_current_pharmacist)
):
    result = await db.execute(
        select(
            models.DoctorPrescription,
            models.Drugs,
            models.ClinicVisit,
            models.DoctorDiagnosis
        )
        .filter(models.DoctorPrescription.student_id == student_id)
        .join(models.Drugs, models.DoctorPrescription.drug_id == models.Drugs.drug_id)
        .join(models.DoctorDiagnosis, models.DoctorPrescription.diagnosis_id == models.DoctorDiagnosis.diagnosis_id)
        .join(models.ClinicVisit, models.DoctorDiagnosis.visit_id == models.ClinicVisit.visit_id)
        .join(models.DrugDispensation, isouter=True)
        .filter(models.DrugDispensation.dispensation_id.is_(None))
    )
    prescriptions = result.all()
    response = [
        {
            "prescription_id": p[0].prescription_id,
            "diagnosis_id": p[0].diagnosis_id,
            "student_id": p[0].student_id,
            "doctor_id": p[0].doctor_id,
            "drug_id": p[0].drug_id,
            "drug_name": p[1].name,
            "dosage": p[0].dosage,
            "instructions": p[0].instructions,
            "visit_id": p[2].visit_id,
            "visit_date": p[2].visit_date,
            "created_at": p[0].created_at
        } for p in prescriptions
    ]
    return response

@router.get("/dispensed_drugs", response_model=List[schemas.DispensationsView])
async def get_dispensed_drugs(
    student_id: int,
    db: AsyncSession = Depends(database.get_db),
    current_user: schemas.TokenData = Depends(get_current_pharmacist)
):
    result = await db.execute(
        select(models.DrugDispensation, models.DispensedDrugs, models.Drugs, models.User)
        .join(models.DispensedDrugs, models.DrugDispensation.dispensation_id == models.DispensedDrugs.prescription_id)
        .join(models.Drugs, models.DispensedDrugs.drug_id == models.Drugs.drug_id)
        .join(models.User, models.DrugDispensation.pharmacist_id == models.User.user_id)
        .filter(models.DrugDispensation.student_id == student_id)
    )
    dispensations = result.all()
    response = [
        {
            "dispensation_id": d[0].dispensation_id,
            "drug_given_id": d[1].drug_given_id,
            "drug": {"name": d[2].name, "drug_id": d[2].drug_id},
            "quantity": d[1].quantity,
            "dispense_date": d[1].dispense_date,
            "pharmacist_name": d[3].username
        } for d in dispensations
    ]
    return response


@router.post("/dispensations", response_model=schemas.DrugDispensationsResponse)
async def create_dispensation(
    dispensation: schemas.DrugDispensationsCreate,
    current_user: schemas.TokenData = Depends(get_current_pharmacist),
    db: AsyncSession = Depends(database.get_db)
):
    # Validate prescription
    result = await db.execute(
        select(models.DoctorPrescription)
        .filter(models.DoctorPrescription.prescription_id == dispensation.prescription_id)
    )
    prescription = result.scalars().first()
    if not prescription:
        raise HTTPException(status_code=404, detail="Prescription not found")
    if prescription.student_id != dispensation.student_id or prescription.drug_id != dispensation.drug_id:
        raise HTTPException(status_code=400, detail="Invalid prescription or drug")

    # Validate stock
    result = await db.execute(
        select(models.Drugs).filter(models.Drugs.drug_id == dispensation.drug_id)
    )
    drug = result.scalars().first()
    if not drug or drug.stock_level < int(dispensation.quantity):
        raise HTTPException(status_code=400, detail="Insufficient drug stock")

    # Get the diagnosis to find the visit_id
    result = await db.execute(
        select(models.DoctorDiagnosis)
        .filter(models.DoctorDiagnosis.diagnosis_id == prescription.diagnosis_id)
    )
    diagnosis = result.scalars().first()
    if not diagnosis:
        raise HTTPException(status_code=404, detail="Diagnosis not found")

    # Create dispensation
    db_dispensation = models.DrugDispensation(
        prescription_id=dispensation.prescription_id,
        student_id=dispensation.student_id,
        pharmacist_id=current_user.user_id
    )
    db.add(db_dispensation)
    await db.flush()

    # Create dispensed drug
    db_dispensed_drug = models.DispensedDrugs(
        prescription_id=db_dispensation.dispensation_id,
        drug_id=dispensation.drug_id,
        quantity=dispensation.quantity,
        dispense_date=dispensation.dispense_date
    )
    db.add(db_dispensed_drug)

    # Update visit status to completed
    await db.execute(
        update(models.ClinicVisit)
        .where(models.ClinicVisit.visit_id == diagnosis.visit_id)
        .values(status=models.VisitStatus.completed)
    )

    # Update stock
    await db.execute(
        update(models.Drugs)
        .where(models.Drugs.drug_id == dispensation.drug_id)
        .values(stock_level=models.Drugs.stock_level - int(dispensation.quantity))
    )

    await db.refresh(db_dispensation)
    return db_dispensation



@router.post("/drugs", response_model=schemas.DrugResponse, status_code=status.HTTP_201_CREATED)
async def create_drug(
    drug: schemas.DrugCreate,
    current_user: schemas.TokenData = Depends(get_current_pharmacist),
    db: AsyncSession = Depends(database.get_db)
):
    result = await db.execute(
        select(models.Drugs).filter(models.Drugs.name == drug.name)
    )
    if result.scalars().first():
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Drug name already exists")

    new_drug = models.Drugs(
        name=drug.name,
        description=drug.description,
        stock_level=drug.stock_level
    )
    db.add(new_drug)
    await db.commit()
    await db.refresh(new_drug)
    return new_drug

@router.put("/drugs/{drug_id}", response_model=schemas.DrugResponse)
async def update_drug(
    drug_id: int,
    drug_update: schemas.DrugUpdate,
    current_user: schemas.TokenData = Depends(get_current_pharmacist),
    db: AsyncSession = Depends(database.get_db)
):
    result = await db.execute(
        select(models.Drugs).filter(models.Drugs.drug_id == drug_id)
    )
    drug = result.scalars().first()
    if not drug:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Drug not found")

    if drug_update.name and drug_update.name != drug.name:
        result = await db.execute(
            select(models.Drugs).filter(models.Drugs.name == drug_update.name)
        )
        if result.scalars().first():
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Drug name already exists")

    update_data = drug_update.dict(exclude_unset=True)
    for key, value in update_data.items():
        setattr(drug, key, value)

    await db.commit()
    await db.refresh(drug)
    return drug

@router.delete("/drugs/{drug_id}", response_model=schemas.MessageResponse)
async def delete_drug(
    drug_id: int,
    current_user: schemas.TokenData = Depends(get_current_pharmacist),
    db: AsyncSession = Depends(database.get_db)
):
    try:
        result = await db.execute(
            select(models.Drugs).filter(models.Drugs.drug_id == drug_id)
        )
        drug = result.scalars().first()
        if not drug:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Drug not found")

        prescription_check = await db.execute(
            select(func.count(models.DoctorPrescription.prescription_id))
            .filter(models.DoctorPrescription.drug_id == drug_id)
        )
        prescription_count = prescription_check.scalar()
        if prescription_count > 0:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Cannot delete drug with existing prescriptions")

        await db.delete(drug)
        await db.commit()
        return {"detail": "Drug deleted successfully"}
    except HTTPException:
        raise
    except Exception as e:
        await db.rollback()
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"Error deleting drug: {str(e)}")


"""
Clinic/
├── assets/
│ └── clinic_bg.jpg
│ └── school_logo.png
│ └── staff_bg.jpg
│ └── user_pics.png
├── Clinic/
│ ├── components/
│ │ ├── admin_side_bar.py
│ │ ├── doctor_side_bar.py
│ │ ├── footer.py
│ │ ├── lab_side_bar.py
│ │ ├── navbar.py
│ │ ├── pharm_side_bar.py
│ │ ├── sign_up.py
│ │ ├── signin.py
│ │ ├── staff_signin.py
│ │ ├── student_side_bar.py
│ ├── pages/
│ │ ├── admin_dashboard.py
│ │ ├── admin_department.py
│ │ ├── admin_faculty.py
│ │ ├── admin_page.py
│ │ ├── admin_student.py
│ │ ├── admin_user.py
│ │ ├── digital_card.py
│ │ ├── doctor_availability.py
│ │ ├── doctor_dashboard.py
│ │ ├── doctor_schedule.py
│ │ ├── doctor_visit.py
│ │ ├── doctor_page.py
│ │ ├── index_page.py
│ │ ├── lab_attendance_page.py
│ │ ├── lab_dashboard.py
│ │ ├── lab_test.py
│ │ ├── pharmercist_page.py
│ │ ├── pharmercist_dashboard.py
│ │ ├── pharmercist_dispensation.py
│ │ ├── pharmercist_drugs.py
│ │ ├── students_complaints.py
│ │ ├── students_dashboard.py
│ │ ├── students_page.py
│ │ ├── super_signup.py
│ ├── services/
│ │ ├── server_requests.py
│ ├── states/
│ │ ├── admin_department_state.py
│ │ ├── admin_faculty_state.py
│ │ ├── admin_state.py
│ │ ├── admin_student_state.py
│ │ ├── auth_state.py
│ │ ├── auth_student.py
│ │ ├── card_state.py
│ │ ├── dispensation_state.py
│ │ ├── doctor_availability_state.py
│ │ ├── doctor_schedule_state.py
│ │ ├── doctor_state.py
│ │ ├── doctor_visit_state.py
│ │ ├── lab_attendance_state.py
│ │ ├── pharmercist_state.py
│ │ ├── pharmercy_drug_state.py
│ │ ├── student_complaint_state.py
│ │ ├── student_state.py
│ ├── Clinic.py
├── rxconfig.py
├── requirements.txt

"""