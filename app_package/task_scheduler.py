import asyncio
from datetime import datetime, timedelta
from sqlalchemy import select, delete
from .database import get_db, engine
from contextlib import asynccontextmanager
from . import models
from sqlalchemy.ext.asyncio import AsyncSession
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
import calendar

scheduler = AsyncIOScheduler()

DAY_MAPPING = {
    "Monday": 0, "Tuesday": 1, "Wednesday": 2,
    "Thursday": 3, "Friday": 4, "Saturday": 5, "Sunday": 6
}

@asynccontextmanager
async def get_db_context():
    gen = get_db()
    try:
        db = await gen.__anext__()
        yield db
    finally:
        try:
            await gen.__anext__()
        except StopAsyncIteration:
            pass

def get_next_week_dates_for_day(day_name: str):
    today = datetime.today().date()
    next_monday = today + timedelta(days=(7 - today.weekday()))
    return [
        next_monday + timedelta(days=i)
        for i in range(7)
        if calendar.day_name[(next_monday + timedelta(days=i)).weekday()] == day_name
    ]

async def generate_schedules():
    async with get_db_context() as db:
        result = await db.execute(
            select(models.Availability).where(models.Availability.status == models.AvailabilityStatus.active)
        )
        availabilities = result.scalars().all()

        for avail in availabilities:
            day = avail.day_of_week.value
            dates = get_next_week_dates_for_day(day)

            for schedule_date in dates:
                start = datetime.combine(schedule_date, avail.start_time)
                end = datetime.combine(schedule_date, avail.end_time)

                slot_start = start
                while slot_start < end:
                    slot_end = slot_start + timedelta(minutes=20)
                    if slot_end > end:
                        break

                    # Prevent duplicates
                    existing = await db.execute(
                        select(models.AppointmentSchedule).filter_by(
                            doctor_id=avail.doctor_id,
                            date=schedule_date,
                            start_time=slot_start.time(),
                            end_time=slot_end.time()
                        )
                    )
                    if not existing.scalar_one_or_none():
                        db.add(models.AppointmentSchedule(
                            doctor_id=avail.doctor_id,
                            availability_id=avail.availability_id,
                            date=schedule_date,
                            start_time=slot_start.time(),
                            end_time=slot_end.time(),
                            status=models.AppointmentStatus.available
                        ))
                    slot_start = slot_end
        await db.commit()
        print(f"[{datetime.now()}] ✔ Schedules generated for next week.")

async def cleanup_past_schedules():
    async with get_db_context() as db:
        today = datetime.today().date()
        result = await db.execute(
            delete(models.AppointmentSchedule)
            .where(
                models.AppointmentSchedule.date < today,
                models.AppointmentSchedule.status == models.AppointmentStatus.available
            )
        )
        await db.commit()
        deleted_count = result.rowcount
        print(f"[{datetime.now()}] 🧹 Cleaned up {deleted_count} past available schedules.")

def start_scheduler():
    # Weekly schedule generation (unchanged)
    scheduler.add_job(generate_schedules, CronTrigger(day_of_week='mon', hour=8, minute=43))
    # Daily cleanup of past available schedules
    scheduler.add_job(cleanup_past_schedules, CronTrigger(hour=8, minute=43))  # Runs daily at 1:00 AM
    scheduler.start()
    print("🕒 APScheduler started.")