# University of Ilorin Clinic Management System (Backend)

## Overview

The University of Ilorin Clinic Management System (Backend) is a FastAPI-based RESTful API designed to manage healthcare services for students and staff at the University of Ilorin. It supports five user roles (admin, doctor, pharmacist, lab attendant, student) and provides comprehensive endpoints for clinic operations. The backend uses PostgreSQL with SQLAlchemy for data persistence, JWT for authentication, and a task scheduler for generating doctor appointment slots.

## Features

### User Roles and Authentication

- **Five Roles**: Admin, Doctor, Pharmacist, Lab Attendant, Student
- **JWT-based Authentication**:
  - Staff login: POST `/auth/user/login`
  - Student login: POST `/auth/student/login`
  - Password reset: POST `/auth/reset-password` (admin-only)

### Comprehensive Role-Based Functionality

- **Admin**: Full system management including user creation, academic data management
- **Doctor**: Appointment scheduling, patient diagnosis, prescription management
- **Pharmacist**: Drug inventory management and prescription dispensation
- **Lab Attendant**: Student health record management
- **Student**: Profile management, appointment booking, health services access

## API Endpoints

The system provides 77 endpoints across 7 routers:

### 1. Authentication Routes (3)

- `POST /auth/user/login` - Staff login (admin, doctor, pharmacist, lab attendant)
- `POST /auth/student/login` - Student login using matric number
- `POST /auth/reset-password` - Password reset (admin-only)

### 2. Admin Routes (24)

**User Management:**
- `POST /admin/users` - Create staff users
- `GET /admin/users` - List all staff users
- `GET /admin/users/{user_id}` - Get user details
- `PUT /admin/users/{user_id}` - Update user details
- `DELETE /admin/users/{user_id}` - Deactivate user

**Student Management:**
- `POST /admin/create-students` - Create students
- `GET /admin/students` - List all students
- `PUT /admin/students/{student_id}` - Update student details
- `DELETE /admin/student/{student_id}` - Deactivate student

**Academic Data Management:**
- `GET /admin/faculties` - List faculties
- `POST /admin/faculties` - Create faculty
- `PUT /admin/update-faculty/{faculty_id}` - Update faculty
- `GET /admin/departments` - List departments
- `POST /admin/departments` - Create department
- `PUT /admin/update-departments/{department_id}` - Update department
- `GET /admin/get-levels` - List academic levels
- `POST /admin/levels` - Create level
- `PUT /admin/update-level/{level_id}` - Update level
- `GET /admin/get-sessions` - List academic sessions
- `POST /admin/sessions` - Create session
- `POST /admin/update-sessions/{session_id}` - Update session

**Dashboard:**
- `GET /admin/admin/get-admin-dashboard` - Admin dashboard stats
- `POST /admin/super-admin/signup` - Super admin registration

### 3. Student Routes (18)

**Profile Management:**
- `POST /students/create-students` - Student registration
- `GET /students/full-profile` - Get complete profile
- `GET /students/me` - Get my profile
- `PUT /students/me` - Update my profile
- `GET /students/me/digital-card` - Get digital clinic card

**Appointments & Health Services:**
- `POST /students/visits` - Create clinic visit
- `GET /students/me/schedules` - Get my schedules
- `POST /students/schedules` - Book schedule
- `GET /students/me/prescriptions` - Get my prescriptions
- `POST /students/complaints` - Submit complaint
- `GET /students/me/all-visits` - Get all my visits
- `GET /students/me/visits/{visit_id}` - Get visit details

**Academic Data:**
- `GET /students/faculties` - List faculties
- `GET /students/read-department/` - List departments
- `GET /students/get-levels` - List levels
- `GET /students/get-sessions` - List sessions

**Dashboard:**
- `GET /students/schedules/available` - View available schedules
- `GET /students/students/me/dashboard` - Student dashboard

### 4. Doctor Routes (18)

**Availability Management:**
- `POST /doctor/availabilities` - Set availability
- `GET /doctor/availabilities` - List availabilities
- `POST /doctor/availability/{availability_id}` - Update availability
- `DELETE /doctor/availability/{availability_id}` - Delete availability

**Schedule Management:**
- `GET /doctor/schedules` - List schedules
- `POST /doctor/schedules` - Create schedule
- `PUT /doctor/schedules/{schedule_id}` - Update schedule
- `PUT /doctor/schedules/{schedule_id}/cancel` - Cancel schedule

**Patient Care:**
- `POST /doctor/visits` - Create visit
- `POST /doctor/diagnoses` - Record diagnosis
- `POST /doctor/prescriptions` - Issue prescription
- `POST /doctor/complaints` - Record complaint
- `POST /doctor/create-multi-prescriptions` - Bulk prescriptions

**Visit Management:**
- `GET /doctor/doctor/visits/{visit_id}/details` - Visit details
- `GET /doctor/doctor/visits` - List all visits
- `GET /doctor/visits/{visit_id}/diagnoses` - Visit diagnoses
- `GET /doctor/visits/{visit_id}/prescriptions` - Visit prescriptions
- `POST /doctor/visits/{visit_id}/complete` - Complete visit

**Dashboard:**
- `GET /doctor/doctors/me/get-doctors-dashboard` - Doctor dashboard

### 5. Pharmacist Routes (7)

**Drug Management:**
- `POST /pharmacist/drugs` - Add drug
- `PUT /pharmacist/drugs/{drug_id}` - Update drug
- `DELETE /pharmacist/drugs/{drug_id}` - Delete drug

**Prescription Management:**
- `GET /pharmacist/students/search` - Search students
- `GET /pharmacist/prescriptions` - List prescriptions
- `GET /pharmacist/dispensed_drugs` - List dispensed drugs
- `POST /pharmacist/dispensations` - Dispense drugs

### 6. Lab Attendant Routes (4)

**Health Records:**
- `POST /lab/create-records/` - Create health record
- `PUT /lab/update-records` - Update record
- `GET /lab/get-all-records/` - List all records
- `GET /lab/get-health-records` - Get specific record

### 7. General Routes (3)

- `GET /general/drugs` - List available drugs
- `GET /general/students/{student_id}` - Get student details
- `GET /general/available-schedules` - List available schedules

## Project Structure

```
clinic/
├── app_package/
│ ├── routers/
│ │ ├── auth.py
│ │ ├── admin.py
│ │ ├── student.py
│ │ ├── doctor.py
│ │ ├── pharmacist.py
│ │ ├── lab_attendant.py
│ │ ├── general.py
│ ├── models.py
│ ├── schemas.py
│ ├── oauth2.py
│ ├── database.py
│ ├── utils.py
├── task_scheduler.py
├── run_server.py
├── requirements.txt
```

## Screenshots 📸

Get a glimpse of route docs !

|                 Shot 1                  |                 Shot 2                  |
|:---------------------------------------:|:---------------------------------------:|
| ![Shot 1](screenshots/Screenshot_1.png) | ![Shot 2](screenshots/Screenshot_2.png) |

|                 Shot 3                  | Shot 4 |
|:---------------------------------------:| :---------------------------------: |
| ![Shot 3](screenshots/Screenshot_5.png) | ![Shot 4](screenshots/Screenshot_6.png) |


## Technologies

- **Framework**: FastAPI
- **Database**: PostgreSQL with SQLAlchemy (asyncpg driver)
- **Authentication**: JWT (python-jose)
- **Password Hashing**: bcrypt (passlib)
- **Task Scheduling**: APScheduler
- **Dependencies**: Pydantic, asyncpg, psycopg2-binary

## Setup Instructions

1. **Clone the Repository**:
    ```bash
    git clone https://github.com/Evayoung/Clinic_System_Backend.git 
    cd clinic-management-backend
    ```

2. **Install Dependencies**:
    ```bash
    pip install -r requirements.txt
    ```

3. **Set Up Environment Variables**:
    - Create a `.env` file:
      ```plaintext
      DATABASE_URL=postgresql+asyncpg://user:password@localhost:5432/clinic
      SECRET_KEY=your-secret-key
      ALGORITHM=HS256
      ACCESS_TOKEN_EXPIRE_MINUTES=30
      ```
    - Generate a `SECRET_KEY` (e.g., using `openssl rand -hex 32`).

4. **Initialize the Database**:
    - Create a PostgreSQL database:
      ```bash
      createdb clinic
      ```
    - Apply migrations (if using Alembic):
      ```bash
      alembic upgrade head
      ```
    - Or run the SQL schema (from `models.py`).

5. **Run the Application**:
    ```bash
    python run_server.py
    ```
    - API will be available at `http://127.0.0.1:8008`.
    - Access Swagger UI at `http://127.0.0.1:8008/docs`.

6. **Run the Task Scheduler**:
    ```bash
    python task_scheduler.py
    ```
    - Generates weekly appointment slots and cleans up unbooked slots.

## Database Schema

Key tables:

- **users**: Stores staff (admin, doctor, pharmacist, lab attendant) with `user_id`, `username`, `password`, `role`, `email`, `status`.
- **students**: Stores student data with `matriculation_number`, `first_name`, `surname`, `email`, `faculty_id`, `department_id`, `level_id`, `session_id`.
- **clinic_cards**: Stores digital clinic cards with `clinic_number`, `student_id`.
- **availabilities**: Stores doctor availability (`doctor_id`, `day_of_week`, `start_time`, `end_time`, `is_available`).
- **appointment_schedules**: Stores 30-minute bookable slots (`schedule_id`, `doctor_id`, `start_time`, `end_time`, `capacity`).
- **clinic_visits**: Stores booked appointments (`visit_id`, `student_id`, `schedule_id`, `visit_date`, `status`).
- **student_complaints**: Stores student complaints (`complaint_id`, `visit_id`, `description`, `complaint_date`).
- **diagnoses**: Stores doctor diagnoses (`diagnosis_id`, `visit_id`, `description`, `diagnosis_date`).
- **prescriptions**: Stores prescriptions (`prescription_id`, `diagnosis_id`, `description`, `prescription_date`).
- **health_records**: Stores lab data (`record_id`, `student_id`, `vitals`, `record_date`).
- **drugs**: Stores drug inventory (`drug_id`, `name`, `quantity`).
- **dispensations**: Stores drug allocations (`dispensation_id`, `student_id`, `drug_id`, `quantity`, `dispensation_date`).
- **access_logs**: Logs user actions (`user_id`, `student_id`, `action`, `ip_address`, `timestamp`).

## Usage

- **Admin**: Create users, academic data, and view drugs via `/admin/*` endpoints.
- **Doctor**: Set availability, view visits/complaints, and issue diagnoses/prescriptions via `/doctor/*` endpoints.
- **Student**: Register, book visits, submit complaints, and view digital cards via `/students/*` endpoints.
- **Pharmacist**: Manage drugs and dispense via `/pharmacist/*` endpoints.
- **Lab Attendant**: Record health data via `/lab/*` endpoints.
- **General**: Access shared data via `/general/*` endpoints.

## Testing

- Use Swagger UI (`/docs`) for interactive testing.
- Sample test data:
  ```sql
  INSERT INTO users (user_id, username, password, role, email, status, created_at)
  VALUES ('UIL/25/0432', 'DrJohn', '$2b$12$<hashed_password>', 'doctor', 'doctor@unilorin.edu.ng', 'active', NOW());

  INSERT INTO students (matriculation_number, first_name, surname, email, faculty_id, department_id, level_id, session_id, password, status, created_at)
  VALUES ('UIL/12345', 'John', 'Doe', 'john.doe@unilorin.edu.ng', 1, 1, 1, 1, '$2b$12$<hashed_password>', 'active', NOW());

Test endpoints with curl or Postman (e.g., POST /auth/user/login, POST /students/visits).

## Contributing
Fork the repository.
Create a feature branch (git checkout -b feature/new-feature).
Commit changes (git commit -m "Add new feature").
Push to the branch (git push origin feature/new-feature).
Open a pull request.

## License
MIT License . See LICENSE for details.

## Contact 📧

For any inquiries or feedback, please reach out to meshelleva@gmail.com or contact Quoin-lab Technologies.

---
**© 2025, Quoin-lab Technologies. All rights reserved.**
