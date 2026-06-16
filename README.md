# نظام إدارة المدرسة — School Management System

<p align="center">
  <img src="images/Gemini_Generated_Image_m3s5rtm3s5rtm3s5.png" alt="School Management System Overview" width="100%"/>
</p>

A comprehensive school management solution built on **Odoo 17 Community Edition**, covering student enrollment, attendance (manual + QR kiosk), grades, fees, timetables, communication, and multi-campus support.

---

## Live System

| | |
|---|---|
| **URL** | https://sms.hdrelhaj.com |
| **Login Page** | https://sms.hdrelhaj.com/web/login |
| **QR Kiosk (Teacher)** | https://sms.hdrelhaj.com/school/qr/scanner?mode=teacher |

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
| Omar Al-Ghamdi | `omar.ghamdi@school.sa` | `School@2026` |
| Maryam Al-Otaibi | `maryam.otaibi@school.sa` | `School@2026` |
| Khalid Al-Dossari | `khalid.dosari@school.sa` | `School@2026` |
| Sara Al-Shehri | `sara.shehri@school.sa` | `School@2026` |
| Hassan Al-Harbi | `hassan.harbi@school.sa` | `School@2026` |
| Wafa Al-Balawi | `wafa.balawi@school.sa` | `School@2026` |

### Teacher (North Campus)

| Name | Login | Password |
|---|---|---|
| Nasser Al-Shammari | `nasser.shammari@northcampus.sa` | `School@2026` |

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
| **Teacher** | Own classes, attendance entry (manual + QR), grade entry |
| **Parent** | Read own children's records (student, fees, attendance, grades) |
| **Student** | Read own profile and academic records |

---

## System Overview

### Modules / Phases

| Phase | Feature |
|---|---|
| 1 | Student, Guardian, Teacher, Class, Academic Year management |
| 2 | Attendance tracking (bulk + individual) |
| 3 | Fee management with payment records and installment scheduling |
| 4 | Grades & Exams (bulk entry, grade sheets) |
| 5 | Dashboard (KPI cards) & Analytics (pivot/graph views) |
| 6 | Timetable management (class + teacher schedules) |
| 7 | Communication (announcements + bulk parent email) |
| 8 | Multi-campus / branch support |
| 9 | **QR Code Attendance** — kiosk scanner, teacher check-in/check-out, QR ID cards |

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
| QR Sessions | 4 (3 closed + 1 open) |
| Teacher Attendance Records | 40 (8 teachers × 5 days) |

---

## QR Attendance — Quick Start

The system includes a **kiosk-based QR attendance module** (`school_qr_attendance`).

**Student attendance flow:**
1. Teacher opens a session: **QR Attendance → Sessions → New**
2. Clicks **🖥️ Open Kiosk** → displays the camera page on a fixed tablet
3. Students walk past and scan their QR card → attendance recorded automatically

**Teacher check-in/check-out:**  
Open `https://sms.hdrelhaj.com/school/qr/scanner?mode=teacher` on an entrance kiosk.  
First scan of the day = check-in. Second scan = check-out (duration calculated automatically).

**Print QR ID cards:**  
Open any student or teacher record → click **🪪 Print QR Card** → A5 PDF with photo + QR code.

---

## Technical Stack

- **Platform:** Odoo 17 Community Edition
- **Database:** PostgreSQL 15 (`demo` database)
- **Deployment:** Docker Compose (`odoo17` + `odoo17-db` + `odoo17-nginx` + `odoo17-certbot`)
- **Reverse Proxy:** nginx with Let's Encrypt SSL (sms.hdrelhaj.com)
- **Custom Modules:**
  - `addons/school_management` — core school ERP (v17.0.8.0.0)
  - `addons/school_qr_attendance` — QR kiosk attendance (v17.0.1.0.0)

### Upgrade Modules

```bash
docker exec odoo17 odoo -c /etc/odoo/odoo.conf -d demo \
  --update school_management,school_qr_attendance --stop-after-init
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

### Renew SSL Certificate

```bash
cd /home/ubuntu/school-management-system
bash renew-ssl.sh
```
