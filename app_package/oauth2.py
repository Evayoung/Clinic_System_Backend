# from datetime import datetime, timedelta
# from jose import JWTError, jwt
# from fastapi import Depends, status, HTTPException
# from fastapi.security import OAuth2PasswordBearer
# from sqlalchemy.orm import Session
#
# from . import models, schemas, database
# from .config import settings
#
# oauth2_scheme = OAuth2PasswordBearer(tokenUrl='login')
#
# SECRET_KEY = settings.SECRET_KEY
# ALGORITHM = settings.ALGORITHM
# ACCESS_TOKEN_EXPIRE_MINUTES = settings.ACCESS_TOKEN_EXPIRE_MINUTES
#
#
# async def create_access_token(data: dict, user_type: str):
#     to_encode = data.copy()
#     expire = datetime.utcnow() + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
#     to_encode.update({'exp': expire, "user_type": user_type})
#     encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
#     return encoded_jwt
#
#
# def verify_access_token(token: str, credentials_exception):
#     try:
#         payload = jwt.decode(token, SECRET_KEY, algorithms=ALGORITHM)
#         user_id: str = payload.get("user_id")
#         user_type: str = payload.get("user_type")
#         if user_id is None or user_type is None:
#             raise credentials_exception
#         token_data = schemas.TokenData(user_id=user_id, user_type=user_type)
#     except JWTError:
#         raise credentials_exception
#     return token_data
#
#
# def get_current_user(token: str = Depends(oauth2_scheme),
#                      db: Session = Depends(database.get_db)
#                      ):
#     credential_exception = HTTPException(
#         status_code=status.HTTP_401_UNAUTHORIZED,
#         detail="Could not validate credentials",
#         headers={"WWW-Authenticate": "Bearer"}
#     )
#
#     # Verify the token and get the token data
#     token_data = verify_access_token(token, credential_exception)
#     # print(token_data)
#
#     if token_data.user_id == "Student":
#         # Fetch the student from the database
#         user = db.query(models.Student).filter(models.Student.matriculation_number == token_data.user_id).first()
#         user_data = schemas.CurrentStudent(
#             name=user.name,
#             matriculation_number=user.matriculation_number,
#             academic_year=user.academic_year,
#             email=user.email,
#             phone=user.phone,
#             role=user.role,
#             faculty=user.faculty,
#             department=user.department
#         )
#     else:
#         user = db.query(models.User).filter(models.User.user_id == token_data.user_id).first()
#         print(user)
#         user_data = schemas.CurrentUser(
#             user_id=user.user_id,
#             name=user.name,
#             email=user.email,
#             phone=user.phone,
#             role=user.role
#         )
#
#     # Check if user is found
#     if user is None:
#         raise credential_exception
#
#     return user_data    # This ensures the correct mapping to the schema
#


from datetime import datetime, timedelta
from jose import JWTError, jwt
from fastapi import Depends, status, HTTPException
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from . import models, schemas, database
from .config import settings

oauth2_scheme = OAuth2PasswordBearer(tokenUrl='/auth/user/login')

SECRET_KEY = settings.SECRET_KEY
ALGORITHM = settings.ALGORITHM
ACCESS_TOKEN_EXPIRE_MINUTES = settings.ACCESS_TOKEN_EXPIRE_MINUTES

async def create_access_token(data: dict):
    to_encode = data.copy()
    expire = datetime.utcnow() + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    to_encode.update({'exp': expire})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt

async def verify_access_token(token: str, credentials_exception):
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        user_id: str = payload.get("user_id")
        student_id: int = payload.get("student_id")
        role: str = payload.get("role")
        if (user_id is None and student_id is None) or role is None:
            raise credentials_exception
        token_data = schemas.TokenData(user_id=user_id, student_id=student_id, role=role)
    except JWTError:
        raise credentials_exception
    return token_data

async def get_current_user(token: str = Depends(oauth2_scheme),
                           db: AsyncSession = Depends(database.get_db)):
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials, please login again",
        headers={"WWW-Authenticate": "Bearer"}
    )

    token_data = await verify_access_token(token, credentials_exception)

    if token_data.student_id:
        # Fetch student
        result = await db.execute(
            select(models.Student).filter(models.Student.student_id == token_data.student_id)
        )
        student = result.scalar_one_or_none()
        if not student:
            raise credentials_exception
        return schemas.StudentResponse.from_orm(student)
    else:
        # Fetch user
        result = await db.execute(
            select(models.User).filter(models.User.user_id == token_data.user_id)
        )
        user = result.scalar_one_or_none()
        if not user:
            raise credentials_exception
        return schemas.UserResponse.from_orm(user)