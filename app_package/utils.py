import random
import string
import re
from datetime import datetime
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from passlib.context import CryptContext
from . import models

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

async def hash_password(password):
    return pwd_context.hash(password)

async def verify_password(plain_password, hashed_password):
    return pwd_context.verify(plain_password, hashed_password)

async def generate_user_id(db: AsyncSession) -> str:
    def generate_id():
        acronym = str(datetime.now())[2:4]
        unique_number = ''.join(random.choices(string.digits, k=3))
        user_id = f"UIL/{acronym}/{unique_number}"
        # Validate format (e.g., UIL/25/123)
        if not re.match(r"^UIL/\d{2}/\d{3}$", user_id):
            raise ValueError("Generated user_id format invalid")
        return user_id

    while True:
        user_id = generate_id()
        result = await db.execute(
            select(models.User).filter(models.User.user_id == user_id)
        )
        existing_user = result.scalar_one_or_none()
        if not existing_user:
            break
    return user_id

async def generate_clinic_number(db: AsyncSession) -> str:
    def generate_number():
        year_acronym = str(datetime.now())[2:4]
        unique_number = ''.join(random.choices(string.digits, k=4))
        clinic_number = f"{unique_number}/{year_acronym}"
        # Validate format (e.g., 1234/25)
        if not re.match(r"^\d{4}/\d{2}$", clinic_number):
            raise ValueError("Generated clinic_number format invalid")
        return clinic_number

    while True:
        clinic_number = generate_number()
        result = await db.execute(
            select(models.ClinicCard).filter(models.ClinicCard.clinic_number == clinic_number)
        )
        existing_card = result.scalar_one_or_none()
        if not existing_card:
            break
    return clinic_number