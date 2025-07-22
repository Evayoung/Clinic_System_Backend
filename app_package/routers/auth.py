from fastapi import APIRouter, Depends, status, HTTPException, Request
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from datetime import datetime
from typing import Union

from sqlalchemy.orm import selectinload

from .. import utils, models, oauth2, database, schemas

router = APIRouter(
    prefix="/auth",
    tags=["Authentication"]
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

@router.post("/user/login", response_model=schemas.UserLoginResponse)
async def login_user(
    user_credentials: schemas.UserLogin,
    db: AsyncSession = Depends(database.get_db),
    request: Request = None
):
    result = await db.execute(select(models.User).filter(models.User.user_id == user_credentials.user_id))
    user = result.scalar_one_or_none()
    if not user:
        # await log_access(db, user_credentials.user_id, None, "failed_user_login", request.client.host)
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid credentials")

    if user.status != models.UserStatus.active:
        # await log_access(db, user_credentials.user_id, None, "inactive_user_login", request.client.host)
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="User account is inactive")

    if not await utils.verify_password(user_credentials.password, user.password):
        # await log_access(db, user_credentials.user_id, None, "failed_user_login", request.client.host)
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid credentials")

    user.last_login = datetime.utcnow()
    await db.commit()

    access_token = await oauth2.create_access_token(data={"user_id": user.user_id, "role": user.role.value})

    # await log_access(db, user.user_id, None, "user_login", request.client.host)
    return {
        "access_token": access_token,
        "token_type": "bearer",
        "username": user.username,
        "user_id": user.user_id,
        "email": user.email,
        "phone": user.phone,
        "role": user.role.value
    }


@router.post("/student/login", response_model=schemas.StudentLoginResponse)
async def login_student(
    student_credentials: schemas.StudentLogin,
    db: AsyncSession = Depends(database.get_db),
    request: Request = None
):
    result = await db.execute(
        select(models.Student)
        .options(
            selectinload(models.Student.faculty),
            selectinload(models.Student.department)
        )
        .filter(models.Student.matriculation_number == student_credentials.matriculation_number)
    )

    student = result.scalar_one_or_none()

    if not student:
        # await log_access(db, None, None, "failed_student_login", request.client.host)
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid credentials")

    if student.status != models.StudentStatus.active:
        # await log_access(db, None, None, "inactive_student_login", request.client.host)
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Student account is inactive")

    if not await utils.verify_password(student_credentials.password, student.password):
        # await log_access(db, None, None, "failed_student_login", request.client.host)
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid credentials")

    student.last_login = datetime.utcnow()
    await db.commit()

    access_token = await oauth2.create_access_token(
        data={"student_id": student.student_id, "role": student.role}
    )

    # await log_access(db, None, student.student_id, "student_login", request.client.host)
    return {
        "access_token": access_token,
        "token_type": "bearer",
        "student_id": student.student_id,
        "matriculation_number": student.matriculation_number,
        "first_name": student.first_name,
        "surname": student.surname,
        "email": student.email,
        "profile_picture": student.profile_picture,
        "faculty_name": student.faculty.faculty_name,
        "department_name": student.department.department_name
    }

@router.post("/reset-password", response_model=schemas.MessageResponse)
async def reset_password(
    reset_data: schemas.PasswordReset,
    db: AsyncSession = Depends(database.get_db),
    current_user: schemas.UserResponse = Depends(oauth2.get_current_user),
    request: Request = None
):
    if current_user.role != models.UserRole.admin:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Admin access required")

    async with db.begin():
        if reset_data.user_id:
            # Reset user password
            result = await db.execute(
                select(models.User).filter(models.User.user_id == reset_data.user_id)
            )
            user = result.scalar_one_or_none()
            if not user:
                raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")

            user.password = await utils.hash_password(reset_data.new_password)
            user.updated_at = datetime.utcnow()
            await db.commit()
            return {"detail": f"Password reset for user {reset_data.user_id}"}

        elif reset_data.student_id:
            # Reset student password
            result = await db.execute(
                select(models.Student).filter(models.Student.matriculation_number == reset_data.student_id)
            )
            student = result.scalar_one_or_none()
            if not student:
                raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Student not found")

            student.password = await utils.hash_password(reset_data.new_password)
            student.updated_at = datetime.utcnow()
            await db.commit()
            return {"detail": f"Password reset for student {reset_data.student_id}"}

        else:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Must provide user_id or student_id")