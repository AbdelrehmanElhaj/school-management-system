# School Management System

A comprehensive school management solution built on **Odoo 17 Community Edition**, covering student enrollment, attendance, grades, fees, timetables, communication, and multi-campus support.

---

## Live System

| | |
|---|---|
| **URL** | http://16.16.124.142:8069 |
| **Login Page** | http://16.16.124.142:8069/web/login |

---

## User Accounts

All accounts use the password **`School@2026`** unless noted otherwise.

### Administrator

| Role | Login | Password |
|---|---|---|
| System Admin | `admin` | `admin` |

### Staff

| Role | Login | Password |
|---|---|---|
| Principal | `ahmed.rashidi@school.sa` | `School@2026` |
| Student Affairs | `affairs@school.sa` | `School@2026` |
| Accountant | `accountant@school.sa` | `School@2026` |

### Teachers (Main Campus)

| Name | Login | Password |
|---|---|---|
| Fatima Al-Zahrani | `fatima.zahrani@school.sa` | `School@2026` |
| Mohammed Al-Qahtani | `mohammed.qahtani@school.sa` | `School@2026` |
| Noura Al-Otaibi | `noura.otaibi@school.sa` | `School@2026` |
| Khalid Al-Ghamdi | `khalid.ghamdi@school.sa` | `School@2026` |
| Sara Al-Shehri | `sara.shehri@school.sa` | `School@2026` |
| Omar Al-Dossari | `omar.dossari@school.sa` | `School@2026` |
| Hessa Al-Maliki | `hessa.maliki@school.sa` | `School@2026` |
| Abdulrahman Al-Harbi | `abdulrahman.harbi@school.sa` | `School@2026` |

### Teacher (North Campus)

| Name | Login | Password |
|---|---|---|
| Maha Al-Anazi | `maha.anazi@school.sa` | `School@2026` |

### Parents

Parents log in with their email address (e.g. `a.harbi@parent.sa`), password `School@2026`.

### Students

Students log in using the format `firstname.STUcode@student.sa` (e.g. `ali.STU20260001@student.sa`), password `School@2026`.

---

## Role Permissions Summary

| Role | Access Level |
|---|---|
| **Admin** | Full access to all modules |
| **Principal** | Read/write most modules; no delete |
| **Affairs** | Manage students, attendance, classes; no fees |
| **Accountant** | Full fee and payment management |
| **Teacher** | Own classes, attendance entry, grade entry |
| **Parent** | Read own children's records (student, fees, attendance, grades) |
| **Student** | Read own profile and academic records |

---

## System Overview

### Modules / Phases

| Phase | Feature |
|---|---|
| 1 | Student, Guardian, Teacher, Class, Academic Year management |
| 2 | Attendance tracking (bulk + individual) |
| 3 | Fee management with payment records |
| 4 | Grades & Exams (bulk entry, grade sheets) |
| 5 | Dashboard (KPI cards) & Analytics (pivot/graph views) |
| 6 | Timetable management (class + teacher schedules) |
| 7 | Communication (announcements + bulk parent email) |
| 8 | Multi-campus / branch support |

### Demo Data Summary

| Entity | Count |
|---|---|
| School Branches | 2 (Main Campus + North Campus) |
| Academic Years | 3 |
| Subjects | 10 |
| Classes | 14 (12 Main + 2 North) |
| Teachers | 9 |
| Guardians | 28 |
| Students | 45 |
| Fee Records | ~180 |
| Attendance Records | ~450 |
| Exams | 8 |
| Grade Records | ~360 |
| Timetable Slots | 25 (Grade 1A full week) |
| Announcements | 4 |

---

## Technical Stack

- **Platform:** Odoo 17 Community Edition
- **Database:** PostgreSQL 15 (`demo` database)
- **Deployment:** Docker (`odoo17` + `odoo17-db` containers)
- **Module path:** `addons/school_management`
- **Module version:** 17.0.8.0.0

### Upgrade Module

```bash
docker exec odoo17 odoo -c /etc/odoo/odoo.conf -d demo \
  --update school_management --stop-after-init
```

### Reload Demo Data

```bash
cd /home/ubuntu/school-management-system
bash setup_demo_data.sh
```

### View Odoo Logs

```bash
docker exec odoo17 tail -f /var/log/odoo/odoo.log
```
