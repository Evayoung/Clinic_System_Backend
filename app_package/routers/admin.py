import base64
import re
from enum import Enum

import aiofiles
from fastapi import APIRouter, Depends, status, HTTPException, Request
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from datetime import datetime
from typing import List, Optional
from pathlib import Path

from sqlalchemy.orm import joinedload

from .. import utils, models, oauth2, database, schemas

router = APIRouter(
    prefix="/admin",
    tags=["Admin"]
)


@router.post("/users", response_model=schemas.UserResponse, status_code=status.HTTP_201_CREATED)
async def create_user(
    user: schemas.UserCreate,
    db: AsyncSession = Depends(database.get_db),
    current_user: schemas.UserResponse = Depends(oauth2.get_current_user),
    request: Request = None
):
    if current_user.role != models.UserRole.admin.value:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Admin access required")

    result = await db.execute(
        select(models.User).filter(models.User.email == user.email)
    )
    existing_user = result.scalar_one_or_none()
    if existing_user:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Email already exists")

    user_id = await utils.generate_user_id(db)
    hashed_password = await utils.hash_password(user.password)

    new_user = models.User(
        user_id=user_id,
        username=user.username,
        password=hashed_password,
        role=user.role,
        email=user.email,
        phone=user.phone,
        status=user.status
    )
    db.add(new_user)
    await db.commit()
    await db.refresh(new_user)

    return new_user



@router.get("/users", response_model=List[schemas.UserResponse])
async def get_users(
    db: AsyncSession = Depends(database.get_db),
    current_user: schemas.UserResponse = Depends(oauth2.get_current_user),
    limit: int = 100,
    offset: int = 0
):
    if current_user.role != models.UserRole.admin.value:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Admin access required")

    result = await db.execute(
        select(models.User).limit(limit).offset(offset)
    )
    users = result.scalars().all()
    return users

@router.get("/users/{user_id}", response_model=schemas.UserResponse)
async def get_user(
    user_id: str,
    db: AsyncSession = Depends(database.get_db),
    current_user: schemas.UserResponse = Depends(oauth2.get_current_user),
    request: Request = None
):
    if current_user.role != models.UserRole.admin.value:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Admin access required")

    result = await db.execute(select(models.User).filter(models.User.user_id == user_id))
    user = result.scalar_one_or_none()

    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")

    # await log_access(db, current_user.user_id, None, f"get_user_{user_id}", request.client.host)
    return user

@router.put("/users/{user_id}", response_model=schemas.UserResponse)
async def update_user(
    user_id: str,
    user_update: schemas.UserUpdate,
    db: AsyncSession = Depends(database.get_db),
    current_user: schemas.UserResponse = Depends(oauth2.get_current_user),
    request: Request = None
):
    if current_user.role != models.UserRole.admin.value:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Admin access required")

    async with db.begin():  # Transaction
        result = await db.execute(select(models.User).filter(models.User.user_id == user_id))
        user = result.scalar_one_or_none()

        if not user:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")

        if user_update.email and user_update.email != user.email:
            result = await db.execute(
                select(models.User).filter(models.User.email == user_update.email)
            )
            if result.scalar_one_or_none():
                raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Email already exists")

        update_data = user_update.dict(exclude_unset=True)
        if "password" in update_data:
            update_data["password"] = await utils.hash_password(update_data["password"])
        for key, value in update_data.items():
            setattr(user, key, value)

        await db.commit()
        await db.refresh(user)

    # await log_access(db, current_user.user_id, None, f"update_user_{user_id}", request.client.host)
    return user

@router.delete("/users/{user_id}", response_model=schemas.MessageResponse)
async def deactivate_user(
    user_id: str,
    db: AsyncSession = Depends(database.get_db),
    current_user: schemas.UserResponse = Depends(oauth2.get_current_user),
    request: Request = None
):
    if current_user.role != models.UserRole.admin.value:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Admin access required")

    async with db.begin():  # Transaction
        result = await db.execute(select(models.User).filter(models.User.user_id == user_id))
        user = result.scalar_one_or_none()

        if not user:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")

        user.status = models.UserStatus.inactive
        await db.commit()

    # await log_access(db, current_user.user_id, None, f"deactivate_user_{user_id}", request.client.host)
    return {"detail": "User deactivated"}



@router.post("/create-students", response_model=schemas.StudentWithRelationsResponse, status_code=status.HTTP_201_CREATED)
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
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST,
                             detail="Matriculation number or email already exists")

        # Get related entities (for both validation and response)
        faculty = await db.execute(
            select(models.Faculty).filter(models.Faculty.faculty_id == student.faculty_id)
        )
        faculty = faculty.scalar_one_or_none()
        if not faculty:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid faculty_id")

        department = await db.execute(
            select(models.Department).filter(models.Department.department_id == student.department_id)
        )
        department = department.scalar_one_or_none()
        if not department:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid department_id")

        level = await db.execute(
            select(models.Level).filter(models.Level.level_id == student.level_id)
        )
        level = level.scalar_one_or_none()
        if not level:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid level_id")

        academic_session = await db.execute(
            select(models.AcademicSession).filter(models.AcademicSession.session_id == student.session_id)
        )
        academic_session = academic_session.scalar_one_or_none()
        if not academic_session:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid session_id")

        # Hash password
        hashed_password = await utils.hash_password(student.password)

        # Handle profile picture
        profile_picture_path = None
        if student.profile_picture:
            try:
                # Remove data URL prefix if present
                profile_picture_base64 = student.profile_picture
                if "," in profile_picture_base64:
                    profile_picture_base64 = profile_picture_base64.split(",")[1]

                # Validate Base64
                try:
                    base64.b64decode(profile_picture_base64, validate=True)
                except Exception as e:
                    raise HTTPException(
                        status_code=status.HTTP_400_BAD_REQUEST,
                        detail=f"Invalid Base64 data for profile picture: {str(e)}"
                    )

                # Create filename and save
                pics_name = student.matriculation_number.replace("/", "-")
                Path("images").mkdir(parents=True, exist_ok=True)
                profile_picture_path = f"images/{pics_name}.jpg"
                async with aiofiles.open(profile_picture_path, "wb") as file_object:
                    await file_object.write(base64.b64decode(profile_picture_base64))
            except Exception as e:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Failed to process profile picture: {str(e)}"
                )

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

        # Return the created student with all relationship names
        return {
            "student_id": new_student.student_id,
            "matriculation_number": new_student.matriculation_number,
            "first_name": new_student.first_name,
            "surname": new_student.surname,
            "email": new_student.email,
            "session_name": academic_session.session_name,
            "phone": new_student.phone,
            "date_of_birth": new_student.date_of_birth,
            "gender": new_student.gender,
            "address": new_student.address,
            "role": new_student.role,
            "faculty_name": faculty.faculty_name,
            "department_name": department.department_name,
            "level_name": level.level_name,
            "emergency_contact": new_student.emergency_contact,
            "profile_picture": new_student.profile_picture,
            "status": new_student.status,
            "created_at": new_student.created_at,
            "updated_at": new_student.updated_at,
            "last_login": new_student.last_login
        }

    except Exception as e:
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to create student: {str(e)}"
        )


@router.get("/students", response_model=List[schemas.StudentWithRelationsResponse])
async def get_all_students(
    db: AsyncSession = Depends(database.get_db),
    limit: int = 100,
    offset: int = 0,
    status: Optional[models.StudentStatus] = None
):
    """
    Get all students with full relationship data (names instead of IDs)
    Only accessible by admin users.
    """

    try:
        # Query with joins to get all related data
        query = (
            select(
                models.Student,
                models.AcademicSession.session_name,
                models.Faculty.faculty_name,
                models.Department.department_name,
                models.Level.level_name
            )
            .join(models.AcademicSession, models.Student.session_id == models.AcademicSession.session_id)
            .join(models.Faculty, models.Student.faculty_id == models.Faculty.faculty_id)
            .join(models.Department, models.Student.department_id == models.Department.department_id)
            .join(models.Level, models.Student.level_id == models.Level.level_id)
        )

        # Apply status filter if provided
        if status:
            query = query.where(models.Student.status == status)

        # Apply pagination
        query = query.limit(limit).offset(offset)

        result = await db.execute(query)
        rows = result.all()

        # Transform the results into our response format
        students = []
        for student, session_name, faculty_name, department_name, level_name in rows:
            student_dict = {
                "student_id": student.student_id,
                "matriculation_number": student.matriculation_number,
                "first_name": student.first_name,
                "surname": student.surname,
                "email": student.email,
                "session_name": session_name,
                "phone": student.phone,
                "date_of_birth": student.date_of_birth,
                "gender": student.gender,
                "address": student.address,
                "role": student.role,
                "faculty_name": faculty_name,
                "department_name": department_name,
                "level_name": level_name,
                "emergency_contact": student.emergency_contact,
                "profile_picture": student.profile_picture,
                "status": student.status,
                "created_at": student.created_at,
                "updated_at": student.updated_at,
                "last_login": student.last_login
            }
            students.append(student_dict)

        return students

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error fetching students: {str(e)}"
        )


@router.put("/students/{student_id}", response_model=schemas.StudentWithRelationsResponse, status_code=status.HTTP_200_OK)
async def update_student(
        student_id: int,
        student_update: schemas.StudentUpdate,
        db: AsyncSession = Depends(database.get_db)
):
    # Get student with all relationships
    result = await db.execute(
        select(models.Student)
        .options(
            joinedload(models.Student.faculty),
            joinedload(models.Student.department),
            joinedload(models.Student.level),
            joinedload(models.Student.academic_session)
        )
        .filter(models.Student.student_id == student_id)
    )
    student = result.scalars().unique().one_or_none()

    if not student:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Student not found")

    # Check email uniqueness if updated
    if student_update.email and student_update.email != student.email:
        result = await db.execute(
            select(models.Student).filter(models.Student.email == student_update.email)
        )
        if result.scalar_one_or_none():
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Email already exists")


    # Prepare update data
    update_data = student_update.dict(exclude_unset=True)

    # Handle password hashing if updated
    if "password" in update_data:
        update_data["password"] = await utils.hash_password(update_data["password"])

    # Handle faculty update (convert name to ID if needed)
    if "faculty" in update_data:
        # If faculty is provided as name, find the corresponding ID
        if isinstance(update_data["faculty"], str):
            faculty = await db.execute(
                select(models.Faculty).filter(models.Faculty.faculty_name == update_data["faculty"])
            )
            faculty = faculty.scalar_one_or_none()
            if not faculty:
                raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid faculty name")
            update_data["faculty_id"] = faculty.faculty_id
            del update_data["faculty"]
        # If faculty is provided as ID, just validate it exists
        else:
            faculty = await db.execute(
                select(models.Faculty).filter(models.Faculty.faculty_id == update_data["faculty"])
            )
            if not faculty.scalar_one_or_none():
                raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid faculty_id")
            update_data["faculty_id"] = update_data["faculty"]
            del update_data["faculty"]

    # Handle department update (similar to faculty)
    if "department" in update_data:
        if isinstance(update_data["department"], str):
            department = await db.execute(
                select(models.Department).filter(models.Department.department_name == update_data["department"])
            )
            department = department.scalar_one_or_none()
            if not department:
                raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid department name")
            update_data["department_id"] = department.department_id
            del update_data["department"]
        else:
            department = await db.execute(
                select(models.Department).filter(models.Department.department_id == update_data["department"])
            )
            if not department.scalar_one_or_none():
                raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid department_id")
            update_data["department_id"] = update_data["department"]
            del update_data["department"]

    # Handle level update
    if "level" in update_data:
        if isinstance(update_data["level"], str):
            level = await db.execute(
                select(models.Level).filter(models.Level.level_name == update_data["level"])
            )
            level = level.scalar_one_or_none()
            if not level:
                raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid level name")
            update_data["level_id"] = level.level_id
            del update_data["level"]
        else:
            level = await db.execute(
                select(models.Level).filter(models.Level.level_id == update_data["level"])
            )
            if not level.scalar_one_or_none():
                raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid level_id")
            update_data["level_id"] = update_data["level"]
            del update_data["level"]

    # Handle session update
    if "session" in update_data:
        if isinstance(update_data["session"], str):
            session = await db.execute(
                select(models.AcademicSession).filter(models.AcademicSession.session_name == update_data["session"])
            )
            session = session.scalar_one_or_none()
            if not session:
                raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid session name")
            update_data["session_id"] = session.session_id
            del update_data["session"]
        else:
            session = await db.execute(
                select(models.AcademicSession).filter(models.AcademicSession.session_id == update_data["session"])
            )
            if not session.scalar_one_or_none():
                raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid session_id")
            update_data["session_id"] = update_data["session"]
            del update_data["session"]

    # Apply updates
    for key, value in update_data.items():
        setattr(student, key, value)

    await db.commit()
    await db.refresh(student)

    # Return the updated student with all relationships
    return {
        "student_id": student.student_id,
        "matriculation_number": student.matriculation_number,
        "first_name": student.first_name,
        "surname": student.surname,
        "email": student.email,
        "session_name": student.academic_session.session_name,
        "phone": student.phone,
        "date_of_birth": student.date_of_birth,
        "gender": student.gender,
        "address": student.address,
        "role": student.role,
        "faculty_name": student.faculty.faculty_name,
        "department_name": student.department.department_name,
        "level_name": student.level.level_name,
        "emergency_contact": student.emergency_contact,
        "profile_picture": student.profile_picture,
        "status": student.status,
        "created_at": student.created_at,
        "updated_at": student.updated_at,
        "last_login": student.last_login
    }




@router.delete("/students/{student_id}", response_model=schemas.MessageResponse)
async def deactivate_student(
    student_id: int,
    db: AsyncSession = Depends(database.get_db),
    current_user: schemas.UserResponse = Depends(oauth2.get_current_user),
    request: Request = None
):
    if current_user.role != models.UserRole.admin.value:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Admin access required")

    async with db.begin():  # Transaction
        result = await db.execute(
            select(models.Student).filter(models.Student.student_id == student_id)
        )
        student = result.scalar_one_or_none()

        if not student:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Student not found")

        student.status = models.StudentStatus.inactive
        await db.commit()

    # await log_access(db, current_user.user_id, student_id, f"deactivate_student_{student_id}", request.client.host)
    return {"detail": "Student deactivated"}

@router.get("/faculties", response_model=List[schemas.FacultyResponse])
async def get_faculties(
    db: AsyncSession = Depends(database.get_db),
    # current_user: schemas.UserResponse = Depends(oauth2.get_current_user),
    request: Request = None,
    limit: int = 100,
    offset: int = 0
):
    # if current_user.role != models.UserRole.admin:
    #     raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Admin access required")

    result = await db.execute(
        select(models.Faculty).limit(limit).offset(offset)
    )
    faculties = result.scalars().all()

    # await log_access(db, current_user.user_id, None, "list_faculties", request.client.host)
    return faculties


@router.post("/faculties", response_model=schemas.FacultyResponse, status_code=status.HTTP_201_CREATED)
async def create_faculty(
        faculty: schemas.FacultyCreate,
        db: AsyncSession = Depends(database.get_db),
        current_user: schemas.UserResponse = Depends(oauth2.get_current_user),
        request: Request = None
):
    if current_user.role != models.UserRole.admin.value:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Admin access required")

    # Check for existing faculty
    result = await db.execute(
        select(models.Faculty).filter(models.Faculty.faculty_name == faculty.faculty_name)
    )
    if result.scalar_one_or_none():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Faculty name already exists"
        )

    try:
        # Create new faculty - ensure faculty_type is properly converted
        new_faculty = models.Faculty(
            faculty_name=faculty.faculty_name,
            faculty_type=faculty.faculty_type.value  # Convert enum to string value
        )

        db.add(new_faculty)
        await db.commit()
        await db.refresh(new_faculty)

        # await log_access(db, current_user.user_id, None, "create_faculty", request.client.host)
        return new_faculty

    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid faculty type: {faculty.faculty_type}. Valid types are: {[t.value for t in schemas.FacultyType]}"
        )


@router.put("/update-faculty/{faculty_id}", response_model=schemas.FacultyResponse)
async def update_faculty(
        faculty_id: int,
        faculty_update: schemas.FacultyUpdate,
        current_user: schemas.TokenData = Depends(oauth2.get_current_user),
        db: AsyncSession = Depends(database.get_db),
        request: Request = None
):
    # 1. Check admin privileges (important for update operations)
    if current_user.role != models.UserRole.admin.value:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Admin access required")

    # 2. Get the faculty to update
    result = await db.execute(select(models.Faculty).filter(models.Faculty.faculty_id == faculty_id))
    faculty = result.scalar_one_or_none()

    if not faculty:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Faculty not found")

    # 3. Check for name uniqueness if name is being changed
    if faculty_update.faculty_name and faculty_update.faculty_name != faculty.faculty_name:
        existing_faculty = await db.execute(
            select(models.Faculty)
            .filter(models.Faculty.faculty_name == faculty_update.faculty_name)
            .filter(models.Faculty.faculty_id != faculty_id)
        )
        if existing_faculty.scalar_one_or_none():
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Faculty name already exists")

    # 4. Handle enum conversion if faculty_type is being updated
    update_data = faculty_update.dict(exclude_unset=True)

    if 'faculty_type' in update_data and isinstance(update_data['faculty_type'], Enum):
        update_data['faculty_type'] = update_data['faculty_type'].value

    # 5. Apply updates
    for key, value in update_data.items():
        setattr(faculty, key, value)

    try:
        await db.commit()
        await db.refresh(faculty)
    except Exception as e:
        await db.rollback()
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"Error updating faculty: {str(e)}")

    # 6. Log the action
    host = request.client.host if request and request.client else "unknown"
    # await log_access(db, current_user.user_id, None, f"update_faculty_{faculty_id}", host)
    return faculty


@router.get("/departments", response_model=List[schemas.DepartmentResponse])
async def get_departments(
        db: AsyncSession = Depends(database.get_db),
        limit: int = 150,
        offset: int = 0
):
    # Join departments with faculties
    result = await db.execute(
        select(
            models.Department,
            models.Faculty.faculty_name
        )
        .join(models.Faculty)
        .limit(limit)
        .offset(offset)
    )

    # Transform results into dictionary format
    departments = []
    for dept, faculty_name in result.all():
        dept_dict = {
            "department_id": dept.department_id,
            "faculty_id": dept.faculty_id,
            "department_name": dept.department_name,
            "faculty_name": faculty_name,
            "created_at": dept.created_at,
            "updated_at": dept.updated_at
        }
        departments.append(dept_dict)

    return departments


@router.post("/departments", response_model=schemas.DepartmentResponse, status_code=status.HTTP_201_CREATED)
async def create_department(
        department: schemas.DepartmentCreate,
        db: AsyncSession = Depends(database.get_db),
        current_user: schemas.UserResponse = Depends(oauth2.get_current_user),
        request: Request = None
):
    # Check admin privileges
    if current_user.role != models.UserRole.admin.value:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin access required"
        )

    # Verify faculty exists
    faculty = await db.execute(
        select(models.Faculty)
        .filter(models.Faculty.faculty_id == department.faculty_id)
    )
    faculty = faculty.scalar_one_or_none()

    if not faculty:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid faculty_id"
        )

    # Check for existing department name in faculty
    existing_dept = await db.execute(
        select(models.Department)
        .filter(
            models.Department.faculty_id == department.faculty_id,
            models.Department.department_name == department.department_name
        )
    )
    if existing_dept.scalar_one_or_none():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Department name already exists in this faculty"
        )

    # Create new department
    new_department = models.Department(
        faculty_id=department.faculty_id,
        department_name=department.department_name
    )
    db.add(new_department)
    await db.commit()
    await db.refresh(new_department)

    # Log the action
    # await log_access(
    #     db,
    #     current_user.user_id,
    #     None,
    #     "create_department",
    #     request.client.host
    # )

    # Return complete department data with faculty info
    return {
        "department_id": new_department.department_id,
        "faculty_id": new_department.faculty_id,
        "department_name": new_department.department_name,
        "faculty_name": faculty.faculty_name,
        "created_at": new_department.created_at,
        "updated_at": new_department.updated_at
    }

@router.put("/update-department/{department_id}", response_model=schemas.DepartmentResponse)
async def update_department(
    department_id: int,
    department_update: schemas.DepartmentUpdate,  # Changed from FacultyUpdate to DepartmentUpdate
    current_user: schemas.TokenData = Depends(oauth2.get_current_user),
    db: AsyncSession = Depends(database.get_db),
    request: Request = None
):
    # 1. Check admin privileges
    if current_user.role != models.UserRole.admin.value:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Admin access required")

    # 2. Get the department to update
    result = await db.execute(
        select(
            models.Department,
            models.Faculty.faculty_name  # Join with faculty to get faculty_name
        )
        .join(models.Faculty)
        .filter(models.Department.department_id == department_id)
    )
    department_data = result.first()

    if not department_data:
        raise HTTPException( status_code=status.HTTP_404_NOT_FOUND, detail="Department not found")

    department, faculty_name = department_data

    # 3. Check for name uniqueness if name is being changed
    if (department_update.department_name and
        department_update.department_name != department.department_name):
        existing_department = await db.execute(
            select(models.Department)
            .filter(models.Department.department_name == department_update.department_name)
            .filter(models.Department.department_id != department_id)
        )
        if existing_department.scalar_one_or_none():
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Department name already exists")

    # 4. Apply updates
    update_data = department_update.dict(exclude_unset=True)
    for key, value in update_data.items():
        setattr(department, key, value)

    try:
        await db.commit()
        await db.refresh(department)
    except Exception as e:
        await db.rollback()
        raise HTTPException( status_code=status.HTTP_400_BAD_REQUEST, detail=f"Error updating department: {str(e)}")

    # 5. Log the action
    host = request.client.host if request and request.client else "unknown"
    # await log_access(db, current_user.user_id, None, f"update_department_{department_id}", host)

    # 6. Return response with faculty_name but without faculty_type
    return {
        "department_id": department.department_id,
        "faculty_id": department.faculty_id,
        "department_name": department.department_name,
        "faculty_name": faculty_name,  # From the joined query
        "created_at": department.created_at,
        "updated_at": department.updated_at
    }



@router.get("/get-levels", response_model=List[schemas.LevelResponse])
async def get_levels(
    db: AsyncSession = Depends(database.get_db),
    current_user: schemas.UserResponse = Depends(oauth2.get_current_user),
    request: Request = None,
    limit: int = 10,
    offset: int = 0
):
    # if current_user.role != models.UserRole.admin.value:
    #     raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Admin access required")

    result = await db.execute(
        select(models.Level).limit(limit).offset(offset)
    )
    levels = result.scalars().all()

    # await log_access(db, current_user.user_id, None, "list_levels", request.client.host)
    return levels


@router.post("/levels", response_model=schemas.LevelResponse, status_code=status.HTTP_201_CREATED)
async def create_level(
    level: schemas.LevelCreate,
    db: AsyncSession = Depends(database.get_db),
    current_user: schemas.UserResponse = Depends(oauth2.get_current_user),
    request: Request = None
):
    if current_user.role != models.UserRole.admin.value:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Admin access required")

    result = await db.execute(
        select(models.Level).filter(models.Level.level_name == level.level_name)
    )
    if result.scalar_one_or_none():
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Level name already exists")

    new_level = models.Level(level_name=level.level_name)
    db.add(new_level)
    await db.commit()
    await db.refresh(new_level)

    # await log_access(db, current_user.user_id, None, "create_level", request.client.host)
    return new_level

@router.put("/update-level/{level_id}", response_model=schemas.LevelResponse)
async def update_level(
    level_id: int,
    level_update: schemas.LevelUpdate,
    current_user: schemas.TokenData = Depends(oauth2.get_current_user),
    db: AsyncSession = Depends(database.get_db),
    request: Request = None
):
    result = await db.execute(
        select(models.Level).filter(models.Level.level_id == level_id)
    )
    level = result.scalar_one_or_none()

    if not level:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Level not found")

    if level_update.level_name != level.level_name:
        result = await db.execute(
            select(models.Level)
            .filter(models.Level.level_name == level_update.level_name)
            .filter(models.Level.level_id != level.level_id)
        )
        if result.scalar_one_or_none():
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Level name already exists")

    # Update fields
    update_data = level_update.dict(exclude_unset=True)
    for key, value in update_data.items():
        setattr(level, key, value)

    await db.commit()
    await db.refresh(level)

    host = request.client.host if request and request.client else "unknown"
    # await log_access(db, current_user.user_id, None, f"update_level_{level_id}", host)
    return level



@router.get("/get-sessions", response_model=List[schemas.AcademicSessionResponse])
async def get_sessions(
    db: AsyncSession = Depends(database.get_db),
    current_user: schemas.UserResponse = Depends(oauth2.get_current_user),
    request: Request = None,
    limit: int = 100,
    offset: int = 0
):
    try:
        # if current_user.role != models.UserRole.admin.value:
        #     raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Admin access required")

        result = await db.execute(
            select(models.AcademicSession).limit(limit).offset(offset)
        )
        sessions = result.scalars().all()

        # await log_access(db, current_user.user_id, None, "list_sessions", request.client.host)
        return sessions
    except Exception as e:
        print(e)
        raise HTTPException(status_code=500, detail=str(e))
        # return []

@router.post("/sessions", response_model=schemas.AcademicSessionResponse, status_code=status.HTTP_201_CREATED)
async def create_session(
    session: schemas.AcademicSessionCreate,
    db: AsyncSession = Depends(database.get_db),
    current_user: schemas.UserResponse = Depends(oauth2.get_current_user),
    request: Request = None
):
    if current_user.role != models.UserRole.admin.value:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Admin access required")

    result = await db.execute(
        select(models.AcademicSession).filter(models.AcademicSession.session_name == session.session_name)
    )
    if result.scalar_one_or_none():
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Session name already exists")

    new_session = models.AcademicSession(session_name=session.session_name)
    db.add(new_session)
    await db.commit()
    await db.refresh(new_session)

    # await log_access(db, current_user.user_id, None, "create_session", request.client.host)
    return new_session


@router.put("/update-session/{session_id}", response_model=schemas.AcademicSessionResponse)
async def update_session(
    session_id: int,
    session_update: schemas.AcademicSessionUpdate,
    current_user: schemas.TokenData = Depends(oauth2.get_current_user),
    db: AsyncSession = Depends(database.get_db),
    request: Request = None
):
    result = await db.execute(
        select(models.AcademicSession).filter(models.AcademicSession.session_id == session_id)
    )
    session = result.scalar_one_or_none()

    if not session:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Session not found")

    if session_update.session_name != session.session_name:
        result = await db.execute(
            select(models.AcademicSession)
            .filter(models.AcademicSession.session_name == session_update.session_name)
            .filter(models.AcademicSession.session_id != session.session_id)
        )
        if result.scalar_one_or_none():
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Session name already exists")

    # Update fields
    update_data = session_update.dict(exclude_unset=True)
    for key, value in update_data.items():
        setattr(session, key, value)

    await db.commit()
    await db.refresh(session)

    return session


@router.get("/admin/get-admin-dashboard", response_model=schemas.AdminDashboardResponse)
async def get_admin_dashboard(
        current_user: schemas.TokenData = Depends(oauth2.get_current_user),
        db: AsyncSession = Depends(database.get_db)
):
    try:
        # Total registered students
        total_students = await db.scalar(
            select(func.count(models.Student.student_id))
            .filter(models.Student.status == models.StudentStatus.active)
        )

        # Total users (all roles)
        total_users = await db.scalar(
            select(func.count(models.User.user_id))
            .filter(models.User.status == models.UserStatus.active)
        )

        # Total registered doctors
        total_doctors = await db.scalar(
            select(func.count(models.User.user_id))
            .filter(
                models.User.role == models.UserRole.doctor,
                models.User.status == models.UserStatus.active
            )
        )

        # Total available drugs (where stock_level > 0)
        total_drugs = await db.scalar(
            select(func.count(models.Drugs.drug_id))
            .filter(models.Drugs.stock_level > 0)
        )

        return {
            "total_students": total_students or 0,
            "total_users": total_users or 0,
            "total_doctors": total_doctors or 0,
            "total_available_drugs": total_drugs or 0
        }

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error fetching admin dashboard data: {str(e)}"
        )


@router.post("/super-admin/signup", response_model=schemas.UserResponse, status_code=status.HTTP_201_CREATED)
async def create_super_admin(
    user: schemas.CreateAdmin,
    db: AsyncSession = Depends(database.get_db)
):
    result = await db.execute(
        select(models.User).filter(models.User.email == user.email)
    )
    existing_user = result.scalar_one_or_none()
    if existing_user:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Email already exists")

    user_id = await utils.generate_user_id(db)
    hashed_password = await utils.hash_password(user.password)

    new_user = models.User(
        user_id=user_id,
        username=user.username,
        password=hashed_password,
        role=models.UserRole.admin,
        email=user.email,
        phone=user.phone,
        status=user.status
    )
    db.add(new_user)
    await db.commit()
    await db.refresh(new_user)

    return new_user
