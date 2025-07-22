import asyncio
import logging
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from starlette.staticfiles import StaticFiles

from .task_scheduler import start_scheduler, generate_schedules, scheduler
from .database import engine
from . import models
from .routers import auth, admin, student, doctor, pharmacist, lab_attendant, general

# logging.basicConfig(level=logging.INFO)
# logger = logging.getLogger(__name__)

description = """
# University of Ilorin Clinic Management System API

Welcome to the **University of Ilorin Clinic Management System API**, a comprehensive platform for managing clinic operations at the University of Ilorin. This API supports authentication, student health records, appointment scheduling, prescriptions, drug inventory, and administrative tasks, serving students, doctors, pharmacists, lab attendants, and administrators with secure, efficient endpoints.

## API Routes Overview

Below is a complete list of all available routes, grouped by functionality:

### 1. Authentication Routes (`/auth`) - 3 Routes
Handles user and student authentication and password management.
- **POST /auth/user/login**: Authenticates staff (e.g., doctors, admins) using a unique user ID and password.
- **POST /auth/student/login**: Authenticates students using their matriculation number and password.
- **POST /auth/reset-password**: Resets a user or student's password (admin-only).

### 2. Admin Routes (`/admin`) - 24 Routes
Manages system-wide operations, restricted to administrators.
- **POST /admin/users**: Creates a new staff user (e.g., doctor, pharmacist).
- **GET /admin/users**: Lists all staff users with pagination.
- **GET /admin/users/{user_id}**: Retrieves details of a specific user.
- **PUT /admin/users/{user_id}**: Updates a user's details.
- **DELETE /admin/users/{user_id}**: Deactivates a user (sets status to inactive).
- **POST /admin/create-students**: Creates a new student.
- **GET /admin/students**: Lists all students with pagination.
- **PUT /admin/students/{student_id}**: Updates a student's details.
- **DELETE /admin/student/{student_id}**: Deactivates a student (sets status to inactive).
- **GET /admin/faculties**: Lists all faculties with pagination.
- **POST /admin/faculties**: Creates a new faculty.
- **PUT /admin/update-faculty/{faculty_id}**: Updates a faculty's details.
- **GET /admin/departments**: Lists all departments with pagination.
- **POST /admin/departments**: Creates a new department.
- **PUT /admin/update-departments/{department_id}**: Updates a department's details.
- **GET /admin/get-levels**: Lists all academic levels with pagination.
- **POST /admin/levels**: Creates a new academic level.
- **PUT /admin/update-level/{level_id}**: Updates an academic level.
- **GET /admin/get-sessions**: Lists all academic sessions with pagination.
- **POST /admin/sessions**: Creates a new academic session.
- **POST /admin/update-sessions/{session_id}**: Updates an academic session.
- **GET /admin/admin/get-admin-dashboard**: Retrieves admin dashboard statistics.
- **POST /admin/super-admin/signup**: Creates a new super admin (restricted).

### 3. Student Routes (`/students`) - 18 Routes
Manages student profiles and clinic interactions.
- **POST /students/create-students**: Creates a new student record.
- **GET /students/full-profile**: Retrieves a student's complete profile.
- **GET /students/me**: Retrieves the logged-in student's profile.
- **PUT /students/me**: Updates the logged-in student's profile.
- **GET /students/me/digital-card**: Retrieves or generates the student's digital clinic card.
- **POST /students/visits**: Creates a new clinic visit record.
- **GET /students/me/schedules**: Lists the student's booked appointment schedules.
- **POST /students/schedules**: Books an available doctor schedule.
- **GET /students/me/prescriptions**: Lists the student's prescriptions.
- **GET /students/faculties**: Lists all faculties.
- **GET /students/read-department/**: Lists all departments.
- **GET /students/get-levels**: Lists all academic levels.
- **GET /students/get-sessions**: Lists all academic sessions.
- **POST /students/complaints**: Records a student's health complaint.
- **GET /students/me/all-visits**: Lists all of the student's clinic visits.
- **GET /students/me/visits/{visit_id}**: Retrieves details of a specific visit.
- **GET /students/schedules/available**: Lists available doctor schedules for booking.
- **GET /students/students/me/dashboard**: Retrieves student dashboard statistics.

### 4. Doctor Routes (`/doctor`) - 18 Routes
Handles doctor-specific operations including availability, schedules, and patient care.
- **POST /doctor/availabilities**: Creates a new availability slot.
- **GET /doctor/availabilities**: Lists doctor's availability slots.
- **POST /doctor/availability/{availability_id}**: Updates an availability slot.
- **DELETE /doctor/availability/{availability_id}**: Deletes an availability slot.
- **GET /doctor/schedules**: Lists doctor's appointment schedules.
- **POST /doctor/schedules**: Creates a new appointment schedule.
- **PUT /doctor/schedules/{schedule_id}**: Updates an appointment schedule.
- **POST /doctor/visits**: Creates a new visit record.
- **POST /doctor/diagnoses**: Records a medical diagnosis.
- **POST /doctor/prescriptions**: Issues a prescription.
- **POST /doctor/complaints**: Records a patient complaint.
- **PUT /doctor/schedules/{schedule_id}/cancel**: Cancels an appointment schedule.
- **GET /doctor/doctor/visits/{visit_id}/details**: Retrieves detailed visit information.
- **GET /doctor/doctors/me/get-doctors-dashboard**: Retrieves doctor dashboard statistics.
- **GET /doctor/doctor/visits**: Lists all visits assigned to the doctor.
- **GET /doctor/visits/{visit_id}/diagnoses**: Retrieves diagnoses for a specific visit.
- **GET /doctor/visits/{visit_id}/prescriptions**: Retrieves prescriptions for a specific visit.
- **POST /doctor/visits/{visit_id}/complete**: Marks a visit as completed.
- **POST /doctor/create-multi-prescriptions**: Creates multiple prescriptions at once.

### 5. Pharmacist Routes (`/pharmacist`) - 7 Routes
Manages drug inventory and prescription dispensations.
- **GET /pharmacist/students/search**: Searches for students by matric number.
- **GET /pharmacist/prescriptions**: Lists undispensed prescriptions.
- **GET /pharmacist/dispensed_drugs**: Lists dispensed drugs.
- **POST /pharmacist/dispensations**: Dispenses drugs based on a prescription.
- **POST /pharmacist/drugs**: Adds a new drug to the inventory.
- **PUT /pharmacist/drugs/{drug_id}**: Updates a drug's details.
- **DELETE /pharmacist/drugs/{drug_id}**: Soft deletes a drug.

### 6. Lab Attendant Routes (`/lab`) - 4 Routes
Manages student health records and lab-related tasks.
- **POST /lab/create-records/**: Creates a new health record for a student.
- **PUT /lab/update-records**: Updates a student's health record.
- **GET /lab/get-all-records/**: Lists all health records.
- **GET /lab/get-health-records**: Retrieves a specific health record.

### 7. General Routes (`/general`) - 3 Routes
Provides public or role-restricted access to shared resources.
- **GET /general/drugs**: Lists all available drugs (public access).
- **GET /general/students/{student_id}**: Retrieves a student's basic details.
- **GET /general/available-schedules**: Lists available doctor schedules for booking.

---

This API ensures scalability and security with JWT authentication, async SQLAlchemy for database operations, and access logging for all endpoints. Explore the endpoints in the Swagger UI (`/docs`) for detailed schemas, request/response examples, and interactive testing.
"""

async def create_tables():
    async with engine.begin() as conn:
        await conn.run_sync(models.Base.metadata.create_all)

# Initialize FastAPI app
app = FastAPI(
    title="WEB BASED CLINIC MANAGEMENT SYSTEM",
    description=description,
    summary="A clinic management system",
    version="0.0.1",
    contact={
        "name": "Quoin-lab Technology",
        "email": "meshelleva@gmail.com",
    },
    license_info={
        "name": "Apache 2.0",
        "url": "https://www.apache.org/licenses/LICENSE-2.0.html",
    }
)

app.mount("/images", StaticFiles(directory="images"), name="images")

# Include routers
app.include_router(auth.router)
app.include_router(admin.router)
app.include_router(student.router)
app.include_router(doctor.router)
app.include_router(pharmacist.router)
app.include_router(lab_attendant.router)
app.include_router(general.router)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Root route
@app.get("/")
async def root():
    return {"message": "University of Ilorin Clinic Management System"}

@app.post("/dev/schedule-generator")
async def trigger_schedule_generation_manually():
    await generate_schedules()
    return {"message": "Schedules generated manually."}


# Create tables on startup
@app.on_event("startup")
async def startup_event():
    await create_tables()
    # await asyncio.sleep(1)
    start_scheduler()

# Shutdown handler
@app.on_event("shutdown")
def shutdown_event():
    if scheduler.running:
        scheduler.shutdown(wait=False)