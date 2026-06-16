#!/bin/bash
# =============================================================================
# School Management System — Demo Database Setup Script
# Drops any existing demo DB, creates a fresh one, installs the module,
# and loads comprehensive realistic data covering all phases (1-8).
#
# Usage:  bash setup_demo_data.sh
# =============================================================================

set -euo pipefail

DB="demo"
ODOO_CONTAINER="odoo17"
DB_CONTAINER="odoo17-db"
DB_USER="odoo17"

GREEN='\033[0;32m'; YELLOW='\033[1;33m'; RED='\033[0;31m'; NC='\033[0m'
info()  { echo -e "${GREEN}[INFO]${NC}  $*"; }
warn()  { echo -e "${YELLOW}[WARN]${NC}  $*"; }
error() { echo -e "${RED}[ERROR]${NC} $*"; exit 1; }

# ---------------------------------------------------------------------------
# 1. Verify containers
# ---------------------------------------------------------------------------
info "Checking containers..."
docker inspect "$ODOO_CONTAINER" --format '{{.State.Running}}' | grep -q true \
    || error "Odoo container ($ODOO_CONTAINER) is not running"
docker inspect "$DB_CONTAINER" --format '{{.State.Running}}' | grep -q true \
    || error "DB container ($DB_CONTAINER) is not running"
info "Containers OK"

# ---------------------------------------------------------------------------
# 2. Drop existing database
# ---------------------------------------------------------------------------
DB_EXISTS=$(docker exec "$DB_CONTAINER" psql -U "$DB_USER" -d postgres -tAc \
    "SELECT 1 FROM pg_database WHERE datname='$DB';" 2>/dev/null || true)

if [ "$DB_EXISTS" = "1" ]; then
    info "Terminating connections and dropping database '$DB'..."
    docker exec "$DB_CONTAINER" psql -U "$DB_USER" -d postgres -c \
        "SELECT pg_terminate_backend(pid)
         FROM pg_stat_activity
         WHERE datname='$DB' AND pid <> pg_backend_pid();" > /dev/null
    docker exec "$DB_CONTAINER" psql -U "$DB_USER" -d postgres \
        -c "DROP DATABASE \"$DB\";"
    info "Database dropped."
fi

# ---------------------------------------------------------------------------
# 3. Create fresh database
# ---------------------------------------------------------------------------
info "Creating fresh database '$DB'..."
docker exec "$DB_CONTAINER" psql -U "$DB_USER" -d postgres \
    -c "CREATE DATABASE \"$DB\" OWNER \"$DB_USER\";"
info "Database '$DB' created."

# ---------------------------------------------------------------------------
# 4. Install school_management module (fresh install, no Odoo demo data)
# ---------------------------------------------------------------------------
info "Installing school_management module (~60 s)..."
docker exec "$ODOO_CONTAINER" odoo \
    -c /etc/odoo/odoo.conf \
    -d "$DB" \
    -i school_management \
    --stop-after-init \
    --without-demo=all
info "Module installed."

# ---------------------------------------------------------------------------
# 5. Load demo data via embedded Python script
# ---------------------------------------------------------------------------
info "Loading demo data..."

docker exec -i "$ODOO_CONTAINER" python3 - <<'PYEOF'
import sys, datetime
import odoo
from odoo import api, SUPERUSER_ID
from odoo.exceptions import ValidationError

DB = "demo"
odoo.tools.config['db_host']     = 'db'
odoo.tools.config['db_user']     = 'odoo17'
odoo.tools.config['db_password'] = 'odoo17'
odoo.tools.config['addons_path'] = (
    '/usr/lib/python3/dist-packages/odoo/addons,'
    '/mnt/extra-addons'
)

registry = odoo.registry(DB)

with registry.cursor() as cr:
    env = api.Environment(cr, SUPERUSER_ID, {})

    # ── helpers ──────────────────────────────────────────────────────────────
    def find(model, domain):
        return env[model].search(domain, limit=1)

    def create_once(model, domain, vals):
        """Return existing record matching domain, or create with vals."""
        rec = env[model].search(domain, limit=1)
        if not rec:
            rec = env[model].create(vals)
            return rec, True   # (record, was_created)
        return rec, False

    def ok(label, created):
        print(f"  {'+ ' if created else '  '}{label}")

    def section(n, total, title):
        print(f"\n[{n}/{total}] {title}")
        print(f"  {'─' * 50}")

    TODAY = datetime.date.today()
    TOTAL = 13

    print()
    print("=" * 64)
    print("  School Management System — Demo Data Loader")
    print(f"  Today: {TODAY}")
    print("=" * 64)

    # =========================================================================
    # 1. School Branches
    # =========================================================================
    section(1, TOTAL, "School Branches")

    main_school, c = create_once('school.branch', [('code', '=', 'MAIN')], {
        'name':    'المدرسة الرئيسية',
        'code':    'MAIN',
        'phone':   '+966112001001',
        'email':   'main@school.sa',
        'address': 'King Fahd Road, Riyadh 11411, Saudi Arabia',
    })
    ok(f"المدرسة الرئيسية  (code: MAIN)", c)

    north, c = create_once('school.branch', [('code', '=', 'NORTH')], {
        'name':    'الحرم الشمالي',
        'code':    'NORTH',
        'phone':   '+966112002001',
        'email':   'north@school.sa',
        'address': 'Prince Mohammed Road, Riyadh 11517, Saudi Arabia',
    })
    ok(f"الحرم الشمالي (code: NORTH)", c)

    # =========================================================================
    # 2. Academic Years
    # =========================================================================
    section(2, TOTAL, "Academic Years")

    ay_prev, c = create_once('school.academic.year', [('code', '=', '2024-2025')], {
        'name':       'السنة الدراسية 2024-2025',
        'code':       '2024-2025',
        'school_id':  main_school.id,
        'date_start': '2024-09-01',
        'date_end':   '2025-06-30',
        'state':      'done',
    })
    ok("2024-2025  المدرسة الرئيسية  (منتهي)", c)

    ay, c = create_once('school.academic.year',
        [('code', '=', '2025-2026'), ('school_id', '=', main_school.id)], {
        'name':       'السنة الدراسية 2025-2026',
        'code':       '2025-2026',
        'school_id':  main_school.id,
        'date_start': '2025-09-01',
        'date_end':   '2026-06-30',
        'state':      'active',
        'current':    True,
    })
    ok("2025-2026  المدرسة الرئيسية  (نشط / حالي)", c)

    ay_north, c = create_once('school.academic.year', [('code', '=', '2025-2026-N')], {
        'name':       'السنة الدراسية 2025-2026 — الشمالي',
        'code':       '2025-2026-N',
        'school_id':  north.id,
        'date_start': '2025-09-01',
        'date_end':   '2026-06-30',
        'state':      'active',
        'current':    False,
    })
    ok("2025-2026-N الحرم الشمالي (نشط)", c)

    # =========================================================================
    # 3. Subjects
    # =========================================================================
    section(3, TOTAL, "Subjects")

    subjects_raw = [
        ('MATH', 'Mathematics'),
        ('SCI',  'Science'),
        ('ENG',  'English Language'),
        ('ARB',  'Arabic Language'),
        ('HIST', 'History'),
        ('GEO',  'Geography'),
        ('PE',   'Physical Education'),
        ('ART',  'Arts & Crafts'),
        ('ICT',  'Information Technology'),
        ('RELG', 'Islamic Studies'),
    ]
    subjects = {}
    for code, name in subjects_raw:
        s, c = create_once('school.subject', [('code', '=', code)],
                           {'name': name, 'code': code})
        ok(f"{code:<6} {name}", c)
        subjects[code] = s

    # =========================================================================
    # 4. Classes
    # =========================================================================
    section(4, TOTAL, "Classes (12 main + 2 north)")

    main_cls_cfg = [
        ('grade1','A',30), ('grade1','B',30),
        ('grade2','A',28), ('grade2','B',28),
        ('grade3','A',30), ('grade3','B',30),
        ('grade4','A',25), ('grade4','B',25),
        ('grade5','A',28), ('grade5','B',28),
        ('grade6','A',25), ('grade6','B',25),
    ]
    north_cls_cfg = [
        ('grade1','A',20),
        ('grade2','A',20),
    ]

    classes = {}
    for grade, sec, cap in main_cls_cfg:
        cls, c = create_once('school.class', [
            ('grade_level', '=', grade),
            ('name', '=', sec),
            ('academic_year_id', '=', ay.id),
        ], {
            'grade_level':      grade,
            'name':             sec,
            'academic_year_id': ay.id,
            'capacity':         cap,
            'state':            'open',
        })
        ok(f"Main   Grade {grade[-1]} Section {sec}", c)
        classes[(grade, sec)] = cls

    north_classes = {}
    for grade, sec, cap in north_cls_cfg:
        cls, c = create_once('school.class', [
            ('grade_level', '=', grade),
            ('name', '=', sec),
            ('academic_year_id', '=', ay_north.id),
        ], {
            'grade_level':      grade,
            'name':             sec,
            'academic_year_id': ay_north.id,
            'capacity':         cap,
            'state':            'open',
        })
        ok(f"North  Grade {grade[-1]} Section {sec}", c)
        north_classes[(grade, sec)] = cls

    # =========================================================================
    # 5. Teachers
    # =========================================================================
    section(5, TOTAL, "Teachers")

    # (name, email, phone, gender, spec, subj_codes, school_id)
    teachers_raw = [
        ('أحمد الرشيدي',   'ahmed.rashidi@school.sa',        '+966501001001', 'male',
         'Mathematics & Science',            ['MATH','SCI'],           main_school.id),
        ('فاطمة الزهراني',  'fatima.zahrani@school.sa',        '+966501001002', 'female',
         'Arabic Language & Islamic Studies', ['ARB','RELG'],           main_school.id),
        ('عمر الغامدي',     'omar.ghamdi@school.sa',           '+966501001003', 'male',
         'English Language',                  ['ENG'],                  main_school.id),
        ('مريم العتيبي',   'maryam.otaibi@school.sa',         '+966501001004', 'female',
         'History & Geography',               ['HIST','GEO'],           main_school.id),
        ('خالد الدوسري',   'khalid.dosari@school.sa',         '+966501001005', 'male',
         'Information Technology',            ['ICT'],                  main_school.id),
        ('سارة الشهري',     'sara.shehri@school.sa',           '+966501001006', 'female',
         'Physical Education & Arts',         ['PE','ART'],             main_school.id),
        ('حسن الحربي',    'hassan.harbi@school.sa',          '+966501001007', 'male',
         'Science & Mathematics',             ['MATH','SCI','ICT'],     main_school.id),
        ('وفاء البلوي',     'wafa.balawi@school.sa',           '+966501001008', 'female',
         'Arabic Language & History',         ['ARB','RELG','HIST'],    main_school.id),
        ('ناصر الشمري', 'nasser.shammari@northcampus.sa',  '+966501002001', 'male',
         'All Subjects (Primary)',            ['MATH','SCI','ENG','ARB'], north.id),
    ]

    teachers = {}
    for name, email, phone, gender, spec, subj_codes, school_id_val in teachers_raw:
        t, c = create_once('school.teacher', [('name', '=', name)], {
            'name':           name,
            'email':          email,
            'phone':          phone,
            'gender':         gender,
            'specialization': spec,
            'school_id':      school_id_val,
            'subject_ids':    [(6, 0, [subjects[cd].id for cd in subj_codes])],
            'qualification':  "Bachelor's in Education",
            'hire_date':      '2020-09-01',
        })
        ok(name, c)
        teachers[name] = t

    ahmed   = teachers['أحمد الرشيدي']
    fatima  = teachers['فاطمة الزهراني']
    omar    = teachers['عمر الغامدي']
    maryam  = teachers['مريم العتيبي']
    khalid  = teachers['خالد الدوسري']
    sara    = teachers['سارة الشهري']
    hassan  = teachers['حسن الحربي']
    wafa    = teachers['وفاء البلوي']
    nasser  = teachers['ناصر الشمري']

    # Assign homeroom teachers and class lists
    homeroom = {
        ('grade1','A'): ahmed,  ('grade1','B'): fatima,
        ('grade2','A'): omar,   ('grade2','B'): ahmed,
        ('grade3','A'): fatima, ('grade3','B'): omar,
        ('grade4','A'): wafa,   ('grade4','B'): wafa,
        ('grade5','A'): maryam, ('grade5','B'): hassan,
        ('grade6','A'): maryam, ('grade6','B'): hassan,
    }
    for key, teacher in homeroom.items():
        classes[key].write({'teacher_id': teacher.id})

    # Teacher → class assignments (many2many)
    ahmed.write({'class_ids':  [(6, 0, [classes[k].id for k in [('grade1','A'),('grade1','B'),('grade2','A'),('grade2','B')]])]})
    fatima.write({'class_ids': [(6, 0, [classes[k].id for k in [('grade1','A'),('grade1','B'),('grade3','A'),('grade3','B')]])]})
    omar.write({'class_ids':   [(6, 0, [classes[k].id for k in [('grade2','A'),('grade2','B'),('grade3','A'),('grade4','A'),('grade4','B')]])]})
    maryam.write({'class_ids': [(6, 0, [classes[k].id for k in [('grade5','A'),('grade5','B'),('grade6','A'),('grade6','B')]])]})
    khalid.write({'class_ids': [(6, 0, [classes[k].id for k in [('grade4','A'),('grade4','B'),('grade5','A'),('grade5','B'),('grade6','A'),('grade6','B')]])]})
    sara.write({'class_ids':   [(6, 0, [classes[k].id for k in [('grade1','A'),('grade2','A'),('grade3','A'),('grade4','A'),('grade5','A'),('grade6','A')]])]})
    hassan.write({'class_ids': [(6, 0, [classes[k].id for k in [('grade5','A'),('grade5','B'),('grade6','A'),('grade6','B')]])]})
    wafa.write({'class_ids':   [(6, 0, [classes[k].id for k in [('grade4','A'),('grade4','B'),('grade5','A'),('grade5','B')]])]})

    for cls in north_classes.values():
        cls.write({'teacher_id': nasser.id})
    nasser.write({'class_ids': [(6, 0, [c.id for c in north_classes.values()])]})

    # Set branch principals
    main_school.write({'principal_id': ahmed.id})
    north.write({'principal_id': nasser.id})

    # =========================================================================
    # 6. Guardians
    # =========================================================================
    section(6, TOTAL, "Guardians")

    guardians_raw = [
        # Main campus (indices 0-21)
        ('عبدالله الحربي',    'father', '+966501003001', 'a.harbi@parent.sa'),
        ('نورة الحربي',        'mother', '+966501003002', 'n.harbi@parent.sa'),
        ('محمد القحطاني',  'father', '+966501003003', 'm.qahtani@parent.sa'),
        ('حصة الشمري',    'mother', '+966501003004', 'h.shammari@parent.sa'),
        ('سعد المطيري',      'father', '+966501003005', 's.mutairi@parent.sa'),
        ('ريم العنزي',        'mother', '+966501003006', 'r.anazi@parent.sa'),
        ('إبراهيم السلمي',    'father', '+966501003007', 'i.sulami@parent.sa'),
        ('منال الغامدي',      'mother', '+966501003008', 'm.ghamdi@parent.sa'),
        ('تركي الزهراني',     'father', '+966501003009', 't.zahrani@parent.sa'),
        ('دلال العتيبي',      'mother', '+966501003010', 'd.otaibi@parent.sa'),
        ('فواز العنزي',       'father', '+966501003011', 'f.enezi@parent.sa'),
        ('سميرة البيشي',      'mother', '+966501003012', 's.bishi@parent.sa'),
        ('وليد الدوسري',    'father', '+966501003013', 'w.dossari@parent.sa'),
        ('ليلى الحمدان',      'mother', '+966501003014', 'l.hamdan@parent.sa'),
        ('سلمان الرشيدي',    'father', '+966501003015', 'sl.rashidi@parent.sa'),
        ('وداد السبيعي',      'mother', '+966501003016', 'w.subaie@parent.sa'),
        ('نايف المالكي',       'father', '+966501003017', 'n.maliki@parent.sa'),
        ('غادة الثبيتي',    'mother', '+966501003018', 'g.thubaiti@parent.sa'),
        ('مشعل الفيفي',      'father', '+966501003019', 'm.faifi@parent.sa'),
        ('هيفاء اليامي',        'mother', '+966501003020', 'h.yami@parent.sa'),
        ('راشد الشهراني',   'father', '+966501003021', 'r.shahrani@parent.sa'),
        ('مريم الخالدي',    'mother', '+966501003022', 'm.khalidi@parent.sa'),
        # North campus (indices 22-27)
        ('عبدالرحمن العقيل', 'father', '+966501004001', 'ar.aqeel@parent.sa'),
        ('سنية العقيل',      'mother', '+966501004002', 'su.aqeel@parent.sa'),
        ('ماجد الشلاّن',      'father', '+966501004003', 'mj.shalan@parent.sa'),
        ('هند الشلاّن',       'mother', '+966501004004', 'hi.shalan@parent.sa'),
        ('فارس الدويش',     'father', '+966501004005', 'fa.duweesh@parent.sa'),
        ('سارة الجهني',       'mother', '+966501004006', 'sa.johani@parent.sa'),
    ]
    guardians = []
    for name, rel, phone, email in guardians_raw:
        g, c = create_once('school.guardian', [('name', '=', name)], {
            'name':         name,
            'relationship': rel,
            'phone':        phone,
            'mobile':       phone,
            'email':        email,
            'address':      'Riyadh, Saudi Arabia',
        })
        ok(name, c)
        guardians.append(g)
    print(f"  → {len(guardians)} guardians total")

    # =========================================================================
    # 7. Students — 42 main + 6 north
    # =========================================================================
    section(7, TOTAL, "Students (42 main + 6 north)")

    saudi = find('res.country', [('code', '=', 'SA')])
    country_id = saudi.id if saudi else False

    # (name, gender, birth_date, class_key, guardian_idx)
    main_students_raw = [
        # ── Grade 1A (4 students) ────────────────────────────────────────────
        ('علي عبدالله الحربي',      'male',   '2017-03-15', ('grade1','A'), 0),
        ('لينا محمد القحطاني',   'female', '2017-07-22', ('grade1','A'), 2),
        ('عمر سعد المطيري',       'male',   '2016-11-05', ('grade1','A'), 4),
        ('ندى إبراهيم السلمي',     'female', '2016-04-18', ('grade1','A'), 6),
        # ── Grade 1B (3 students) ────────────────────────────────────────────
        ('يوسف تركي الزهراني',   'male',   '2017-08-30', ('grade1','B'), 8),
        ('هيا فواز العنزي',        'female', '2017-02-14', ('grade1','B'), 10),
        ('فيصل وليد الدوسري',   'male',   '2017-05-20', ('grade1','B'), 12),
        # ── Grade 2A (4 students) ────────────────────────────────────────────
        ('غيداء سلمان الرشيدي',   'female', '2015-12-10', ('grade2','A'), 14),
        ('ريان نايف المالكي',       'male',   '2015-06-25', ('grade2','A'), 16),
        ('سارة مشعل الفيفي',       'female', '2015-09-08', ('grade2','A'), 18),
        ('ماجد راشد الشهراني',   'male',   '2015-01-17', ('grade2','A'), 20),
        # ── Grade 2B (3 students) ────────────────────────────────────────────
        ('أروى عبدالله الحربي',     'female', '2015-04-02', ('grade2','B'), 1),
        ('خالد محمد القحطاني', 'male',   '2015-10-28', ('grade2','B'), 3),
        ('دانة سعد المطيري',       'female', '2015-07-15', ('grade2','B'), 5),
        # ── Grade 3A (4 students) ────────────────────────────────────────────
        ('بندر إبراهيم السلمي',   'male',   '2014-03-22', ('grade3','A'), 7),
        ('رند تركي الزهراني',      'female', '2014-11-30', ('grade3','A'), 9),
        ('نواف فواز العنزي',       'male',   '2014-08-12', ('grade3','A'), 11),
        ('غلا وليد الدوسري',    'female', '2014-05-05', ('grade3','A'), 13),
        # ── Grade 3B (3 students) ────────────────────────────────────────────
        ('سعود سلمان الرشيدي',     'male',   '2013-02-18', ('grade3','B'), 15),
        ('لجين نايف المالكي',      'female', '2013-06-24', ('grade3','B'), 17),
        ('بدر مشعل الفيفي',       'male',   '2013-10-03', ('grade3','B'), 19),
        # ── Grade 4A (3 students) ────────────────────────────────────────────
        ('ريما راشد الشهراني',   'female', '2012-08-15', ('grade4','A'), 21),
        ('سلطان عبدالله الحربي',   'male',   '2012-03-07', ('grade4','A'), 0),
        ('فاطمة محمد القحطاني', 'female', '2013-11-19', ('grade4','A'), 2),
        # ── Grade 4B (3 students) ────────────────────────────────────────────
        ('نايف سعد المطيري',      'male',   '2013-04-25', ('grade4','B'), 4),
        ('ديمة إبراهيم السلمي',     'female', '2012-09-11', ('grade4','B'), 6),
        ('حمد تركي الزهراني',     'male',   '2012-07-28', ('grade4','B'), 8),
        # ── Grade 5A (3 students) ────────────────────────────────────────────
        ('مها فواز العنزي',        'female', '2012-01-14', ('grade5','A'), 10),
        ('طارق وليد الدوسري',    'male',   '2011-11-22', ('grade5','A'), 12),
        ('هند سلمان الرشيدي',     'female', '2011-06-08', ('grade5','A'), 14),
        # ── Grade 5B (3 students) ────────────────────────────────────────────
        ('أسامة نايف المالكي',       'male',   '2011-08-30', ('grade5','B'), 16),
        ('أسماء مشعل الفيفي',       'female', '2010-12-18', ('grade5','B'), 18),
        ('يزيد راشد الشهراني',  'male',   '2010-09-05', ('grade5','B'), 20),
        # ── Grade 6A (3 students) ────────────────────────────────────────────
        ('أبرار عبدالله الحربي',    'female', '2010-04-27', ('grade6','A'), 1),
        ('راشد محمد القحطاني', 'male',   '2009-11-14', ('grade6','A'), 3),
        ('ليلى سعد المطيري',      'female', '2009-07-20', ('grade6','A'), 5),
        # ── Grade 6B (3 students) ────────────────────────────────────────────
        ('مشعل إبراهيم السلمي',   'male',   '2009-03-09', ('grade6','B'), 7),
        ('تهاني تركي الزهراني',    'female', '2009-10-31', ('grade6','B'), 9),
        ('فراس فواز العنزي',       'male',   '2010-02-16', ('grade6','B'), 11),
    ]

    north_students_raw = [
        ('نور عبدالرحمن العقيل',   'female', '2017-05-10', ('grade1','A'), 22),
        ('طارق ماجد الشلاّن',       'male',   '2017-09-23', ('grade1','A'), 24),
        ('ريما فارس الدويش',       'female', '2017-01-07', ('grade1','A'), 26),
        ('خالد عبدالرحمن العقيل', 'male',   '2015-08-14', ('grade2','A'), 23),
        ('دينا ماجد الشلاّن',        'female', '2015-11-29', ('grade2','A'), 25),
        ('سامي فارس الدويش',       'male',   '2016-03-18', ('grade2','A'), 27),
    ]

    students = []
    for name, gender, bdate, cls_key, g_idx in main_students_raw:
        s, c = create_once('school.student', [('name', '=', name)], {
            'name':            name,
            'gender':          gender,
            'birth_date':      bdate,
            'nationality':     country_id,
            'class_id':        classes[cls_key].id,
            'guardian_id':     guardians[g_idx].id,
            'enrollment_date':  '2025-09-01',
            'status':           'active',
            'enrollment_state': 'active',
        })
        ok(name, c)
        students.append(s)

    north_students = []
    for name, gender, bdate, cls_key, g_idx in north_students_raw:
        s, c = create_once('school.student', [('name', '=', name)], {
            'name':            name,
            'gender':          gender,
            'birth_date':      bdate,
            'nationality':     country_id,
            'class_id':        north_classes[cls_key].id,
            'guardian_id':     guardians[g_idx].id,
            'enrollment_date': '2025-09-01',
            'status':          'active',
            'enrollment_state': 'active',
        })
        ok(name, c)
        north_students.append(s)

    all_students = students + north_students
    cr.commit()
    print(f"  → {len(students)} main  +  {len(north_students)} north  =  {len(all_students)} students total")

    # =========================================================================
    # 8. Fees — varied payment states for dashboard realism
    # =========================================================================
    section(8, TOTAL, "Fees & Payments")

    tuition_type  = find('school.fee.type', [('code', '=', 'TUITION')])
    reg_type      = find('school.fee.type', [('code', '=', 'REGISTRATION')])
    activity_type = find('school.fee.type', [('code', '=', 'ACTIVITY')])

    grade_num = {f'grade{i}': i for i in range(1, 13)}

    def tuition_amount(student):
        gn = grade_num.get(student.class_id.grade_level, 1)
        return round((5000 + gn * 500) / 3, 2)

    def create_fee(student, fee_type, term, amount, due_date):
        f, _ = create_once('school.fee', [
            ('student_id', '=', student.id),
            ('fee_type_id', '=', fee_type.id),
            ('term', '=', term),
            ('academic_year_id', '=', student.class_id.academic_year_id.id),
        ], {
            'student_id':   student.id,
            'fee_type_id':  fee_type.id,
            'amount':       amount,
            'term':         term,
            'invoice_date': '2025-09-01',
            'due_date':     due_date,
        })
        if f.state == 'draft':
            f.action_confirm()
        return f

    def pay_fee(fee, amount, date, method='bank_transfer'):
        if fee.balance <= 0:
            return
        pay_amount = min(amount, fee.balance)
        wiz = env['school.fee.payment.wizard'].create({
            'fee_id':         fee.id,
            'amount':         round(pay_amount, 2),
            'payment_date':   date,
            'payment_method': method,
        })
        wiz.action_confirm()

    fee_count = 0
    pay_count = 0

    for idx, s in enumerate(all_students):
        amt = tuition_amount(s)
        is_north = s in north_students

        # Registration — all students pay this
        f_reg = create_fee(s, reg_type, 'annual', 500.0, '2025-09-15')
        pay_fee(f_reg, 500.0, '2025-09-10', 'cash')
        fee_count += 1; pay_count += 1

        # Term 1 tuition  (due 2025-10-15)
        f1 = create_fee(s, tuition_type, 'first', amt, '2025-10-15')
        fee_count += 1
        if is_north or idx < 20:
            # North + first 20 main students: PAID in full
            pay_fee(f1, amt, '2025-10-12', 'bank_transfer')
            pay_count += 1
        elif idx < 30:
            # Students 20-29: partial payment (50%)
            pay_fee(f1, round(amt * 0.5, 2), '2025-10-20', 'cash')
            pay_count += 1
        # else: students 30+ → unpaid (will become overdue)

        # Term 2 tuition  (due 2026-01-15)
        f2 = create_fee(s, tuition_type, 'second', amt, '2026-01-15')
        fee_count += 1
        if is_north or idx < 10:
            pay_fee(f2, amt, '2026-01-12', 'bank_transfer')
            pay_count += 1
        elif idx < 20:
            pay_fee(f2, round(amt * 0.6, 2), '2026-01-20', 'cash')
            pay_count += 1

        # Term 3 tuition  (due 2026-04-15)
        f3 = create_fee(s, tuition_type, 'third', amt, '2026-04-15')
        fee_count += 1
        if is_north or idx < 8:
            pay_fee(f3, amt, '2026-04-10', 'bank_transfer')
            pay_count += 1

        # Activity fee — first 15 main students
        if activity_type and idx < 15 and not is_north:
            fa = create_fee(s, activity_type, 'annual', 300.0, '2025-10-01')
            pay_fee(fa, 300.0, '2025-09-28', 'cash')
            fee_count += 1; pay_count += 1

    # Mark all past-due unpaid fees as overdue (simulate cron)
    overdue = env['school.fee'].search([
        ('state', '=', 'due'),
        ('due_date', '<', str(TODAY)),
    ])
    if overdue:
        overdue.write({'state': 'overdue'})

    cr.commit()
    print(f"  → {fee_count} fees created,  {pay_count} payments confirmed")
    overdue_count = env['school.fee'].search_count([('state', '=', 'overdue')])
    paid_count    = env['school.fee'].search_count([('state', '=', 'paid')])
    partial_count = env['school.fee'].search_count([('state', '=', 'partial')])
    print(f"  → paid: {paid_count}  partial: {partial_count}  overdue: {overdue_count}")

    # =========================================================================
    # 9. Attendance — 4 classes × 6 weeks, Saudi school week Sun-Thu
    # =========================================================================
    section(9, TOTAL, "Attendance (6 weeks × Sun–Thu)")

    # Sunday Oct 5, 2025 is the start of week 1
    # Python: weekday()=6 for Sunday; Oct 5 2025 = Sunday ✓
    WEEK1_START = datetime.date(2025, 10, 5)

    attend_classes = [
        ('grade1','A'),
        ('grade2','A'),
        ('grade3','A'),
        ('grade4','A'),
    ]

    att_count = 0
    Att = env['school.attendance']

    for cls_key in attend_classes:
        cls = classes[cls_key]
        cls_students = env['school.student'].search([
            ('class_id', '=', cls.id),
            ('status',   '=', 'active'),
        ])
        for week in range(6):
            for day_offset in range(5):   # 0=Sun … 4=Thu
                att_date = WEEK1_START + datetime.timedelta(days=week * 7 + day_offset)
                for pos, st in enumerate(cls_students):
                    if Att.search([('student_id','=',st.id),('date','=',str(att_date))],limit=1):
                        continue
                    # Attendance pattern:
                    #   pos 0 (first student): absent Wednesday of weeks 2 & 4
                    #   pos 1 (second student): late Monday every week; absent Thu of week 5
                    #   pos 2 (third student): excused Thursday of week 3
                    #   all others: present
                    if   pos == 0 and day_offset == 3 and week in (1, 3):
                        status = 'absent'
                    elif pos == 1 and day_offset == 1:
                        status = 'late'
                    elif pos == 1 and day_offset == 4 and week == 4:
                        status = 'absent'
                    elif pos == 2 and day_offset == 4 and week == 2:
                        status = 'excused'
                    else:
                        status = 'present'
                    Att.create({
                        'student_id': st.id,
                        'class_id':   cls.id,
                        'date':       str(att_date),
                        'status':     status,
                    })
                    att_count += 1

    cr.commit()
    print(f"  → {att_count} attendance records created")

    # =========================================================================
    # 10. Exams & Grades
    # =========================================================================
    section(10, TOTAL, "Exams & Grades")

    # Scores by first-two-name fragment (Arabic)
    score_map = {
        'علي عبدالله':    88, 'لينا محمد':    93, 'عمر سعد':       76,
        'ندى إبراهيم':    95, 'يوسف تركي':   81, 'هيا فواز':      70,
        'فيصل وليد':      65, 'غيداء سلمان':  78, 'ريان نايف':     84,
        'سارة مشعل':      90, 'ماجد راشد':    79, 'أروى عبدالله':  88,
        'خالد محمد':      72, 'دانة سعد':     85, 'بندر إبراهيم':  62,
        'رند تركي':       77, 'نواف فواز':    94, 'غلا وليد':      86,
        'سعود سلمان':     71, 'لجين نايف':    97, 'بدر مشعل':      68,
        'ريما راشد':      83, 'سلطان عبدالله':74, 'فاطمة محمد':    89,
        'نايف سعد':       60, 'ديمة إبراهيم': 92, 'حمد تركي':      73,
        'مها فواز':       87, 'طارق وليد':    66, 'هند سلمان':     91,
        'أسامة نايف':     79, 'أسماء مشعل':   82, 'يزيد راشد':     58,
        'أبرار عبدالله':  96, 'راشد محمد':    69, 'ليلى سعد':      85,
        'مشعل إبراهيم':   77, 'تهاني تركي':   93, 'فراس فواز':     64,
    }

    def get_score(student_name):
        for frag, sc in score_map.items():
            if frag in student_name:
                return sc
        return 75  # default

    exams_cfg = [
        # (name, subj_code, class_key, date, term, max_score, pass_score)
        ('اختبار منتصف الفصل — الرياضيات — الصف الأول أ',    'MATH', ('grade1','A'), '2025-11-15', 'first',  100.0, 50.0),
        ('اختبار منتصف الفصل — اللغة الإنجليزية — الصف الأول أ', 'ENG', ('grade1','A'), '2025-11-17', 'first',  100.0, 50.0),
        ('اختبار منتصف الفصل — اللغة العربية — الصف الثاني أ',  'ARB', ('grade2','A'), '2025-11-18', 'first',  100.0, 50.0),
        ('اختبار منتصف الفصل — العلوم — الصف الثالث أ',        'SCI', ('grade3','A'), '2025-11-20', 'first',  100.0, 50.0),
        ('اختبار منتصف الفصل — الحاسب الآلي — الصف الرابع أ',  'ICT', ('grade4','A'), '2025-11-22', 'first',  100.0, 50.0),
        ('الاختبار النهائي — الرياضيات — الصف الأول أ',         'MATH', ('grade1','A'), '2026-02-10', 'second', 100.0, 50.0),
        ('الاختبار النهائي — اللغة الإنجليزية — الصف الثاني أ', 'ENG', ('grade2','A'), '2026-02-12', 'second', 100.0, 50.0),
        ('الاختبار النهائي — الرياضيات — الصف السادس أ',        'MATH', ('grade6','A'), '2026-05-10', 'third',  100.0, 50.0),
    ]

    exam_count  = 0
    grade_count = 0

    for exam_name, subj_code, cls_key, exam_date, term, max_sc, pass_sc in exams_cfg:
        ex, c = create_once('school.exam', [('name', '=', exam_name)], {
            'name':             exam_name,
            'subject_id':       subjects[subj_code].id,
            'class_id':         classes[cls_key].id,
            'academic_year_id': ay.id,
            'date':             exam_date,
            'max_score':        max_sc,
            'pass_score':       pass_sc,
            'term':             term,
            'exam_type':        'midterm' if 'Mid' in exam_name else 'final',
        })
        if ex.state == 'draft':
            ex.action_confirm()
        if c:
            exam_count += 1
            ok(exam_name, True)

        cls_students = env['school.student'].search([
            ('class_id', '=', classes[cls_key].id),
            ('status',   '=', 'active'),
        ])
        new_grades = 0
        for st in cls_students:
            if not find('school.grade', [('student_id','=',st.id),('exam_id','=',ex.id)]):
                env['school.grade'].create({
                    'student_id': st.id,
                    'exam_id':    ex.id,
                    'score':      get_score(st.name),
                    'notes':      'اختبار منتصف الفصل' if 'منتصف' in exam_name else 'الاختبار النهائي',
                })
                new_grades  += 1
                grade_count += 1
        if new_grades and ex.state == 'confirmed':
            try: ex.action_grade()
            except Exception: pass

    cr.commit()
    print(f"  → {exam_count} exams,  {grade_count} grade records")

    # =========================================================================
    # 11. Timetable — Grade 1A active timetable (5 days × 5 periods)
    # =========================================================================
    section(11, TOTAL, "Timetable  (Grade 1A — 25 slots)")

    periods = env['school.period'].search(
        [('is_break', '=', False), ('active', '=', True)], order='sequence'
    )

    if len(periods) >= 5:
        tt, c = create_once('school.timetable',
            [('class_id', '=', classes[('grade1','A')].id),
             ('name', '=', 'Main Timetable 2025-2026')],
            {
                'name':     'Main Timetable 2025-2026',
                'class_id': classes[('grade1','A')].id,
            })
        ok("Grade 1A — Main Timetable 2025-2026", c)

        p = list(periods[:5])   # 5 teaching periods (breaks excluded)

        # (day_str, period_index, subject_code, teacher_record)
        # Days: '0'=Sun, '1'=Mon, '2'=Tue, '3'=Wed, '4'=Thu
        schedule = [
            # Sunday
            ('0', 0, 'MATH', ahmed), ('0', 1, 'SCI',  ahmed),
            ('0', 2, 'ARB',  fatima),('0', 3, 'RELG', fatima),('0', 4, 'ENG', omar),
            # Monday
            ('1', 0, 'ENG',  omar),  ('1', 1, 'MATH', ahmed),
            ('1', 2, 'ARB',  fatima),('1', 3, 'SCI',  ahmed), ('1', 4, 'RELG',fatima),
            # Tuesday
            ('2', 0, 'ARB',  fatima),('2', 1, 'ENG',  omar),
            ('2', 2, 'MATH', ahmed), ('2', 3, 'SCI',  ahmed), ('2', 4, 'ART', sara),
            # Wednesday
            ('3', 0, 'SCI',  ahmed), ('3', 1, 'ARB',  fatima),
            ('3', 2, 'ENG',  omar),  ('3', 3, 'MATH', ahmed), ('3', 4, 'PE',  sara),
            # Thursday
            ('4', 0, 'MATH', ahmed), ('4', 1, 'ARB',  fatima),
            ('4', 2, 'ENG',  omar),  ('4', 3, 'RELG', fatima),('4', 4, 'ART', sara),
        ]

        slot_count = 0
        Slot = env['school.timetable.slot']
        for day_str, p_idx, subj_code, teacher in schedule:
            period = p[p_idx]
            if not Slot.search([
                ('timetable_id', '=', tt.id),
                ('day_of_week',  '=', day_str),
                ('period_id',    '=', period.id),
            ], limit=1):
                Slot.create({
                    'timetable_id': tt.id,
                    'day_of_week':  day_str,
                    'period_id':    period.id,
                    'subject_id':   subjects[subj_code].id,
                    'teacher_id':   teacher.id,
                })
                slot_count += 1

        if tt.state == 'draft':
            tt.action_activate()

        cr.commit()
        print(f"  → {slot_count} timetable slots created, status: {tt.state}")
    else:
        print("  ⚠  Not enough periods configured — skipping timetable")

    # =========================================================================
    # 12. Announcements
    # =========================================================================
    section(12, TOTAL, "Announcements")

    announcements_raw = [
        {
            'name':         'أهلاً بالعودة — السنة الدراسية 2025-2026',
            'body':         '<p>أعزاءنا أولياء الأمور والطلاب،</p>'
                            '<p>يسعدنا الترحيب بجميع الطلاب والأسر في بداية العام الدراسي الجديد 2025-2026. '
                            'تبدأ الدراسة يوم الأحد 7 سبتمبر 2025.</p>'
                            '<p>نتمنى للجميع عاماً دراسياً مثمراً وناجحاً.</p>',
            'date_publish': '2025-09-01',
            'date_expire':  '2025-09-15',
            'audience':     'all',
            'send_email':   False,
        },
        {
            'name':         'جدول اختبارات منتصف الفصل — نوفمبر 2025',
            'body':         '<p>تُعقد اختبارات منتصف الفصل من <strong>15 إلى 22 نوفمبر 2025</strong>.</p>'
                            '<ul><li>الصف الأول: الرياضيات واللغة الإنجليزية</li>'
                            '<li>الصف الثاني: اللغة العربية والعلوم</li>'
                            '<li>الصفوف 3-6: جميع المواد</li></ul>'
                            '<p>يرجى التأكد من استعداد الطلاب للاختبارات.</p>',
            'date_publish': '2025-10-20',
            'date_expire':  '2025-11-23',
            'audience':     'all',
            'send_email':   False,
        },
        {
            'name':         'اليوم الوطني السعودي — إجازة 23 سبتمبر',
            'body':         '<p>بمناسبة اليوم الوطني السعودي، ستكون المدرسة <strong>مغلقة يوم الثلاثاء 23 سبتمبر 2025</strong>.</p>'
                            '<p>نفخر بالاحتفال باليوم الوطني للمملكة العربية السعودية 95. '
                            'تستأنف الدراسة يوم الأحد 28 سبتمبر 2025.</p>',
            'date_publish': '2025-09-20',
            'date_expire':  '2025-09-25',
            'audience':     'all',
            'send_email':   False,
        },
        {
            'name':         'اجتماع أولياء الأمور والمعلمين — 10 ديسمبر 2025',
            'body':         '<p>ندعو جميع أولياء الأمور لحضور <strong>اجتماع أولياء الأمور والمعلمين</strong> يوم الأربعاء 10 ديسمبر 2025.</p>'
                            '<p>المواعيد: 4:00 م – 7:00 م. يرجى حجز موعدكم عبر مكتب المدرسة.</p>',
            'date_publish': '2025-11-25',
            'date_expire':  '2025-12-11',
            'audience':     'parents',
            'send_email':   False,
        },
    ]

    ann_count = 0
    for data in announcements_raw:
        ann, c = create_once('school.announcement', [('name', '=', data['name'])], data)
        if ann.state == 'draft':
            ann.action_publish()
        ok(data['name'], c)
        ann_count += 1

    cr.commit()
    print(f"  → {ann_count} announcements published")

    # =========================================================================
    # 13. Summary
    # =========================================================================
    section(13, TOTAL, "Summary")

    print()
    print("=" * 64)
    print("  Demo data load complete!")
    print("=" * 64)

    def count(model, domain=None):
        return env[model].search_count(domain or [])

    rows = [
        ("School Branches",   count('school.branch')),
        ("Academic Years",    count('school.academic.year')),
        ("Subjects",          count('school.subject')),
        ("Classes",           count('school.class')),
        ("Teachers",          count('school.teacher')),
        ("Guardians",         count('school.guardian')),
        ("Students",          count('school.student')),
        ("  └ Active",        count('school.student', [('status','=','active')])),
        ("Fees (total)",      count('school.fee')),
        ("  └ Paid",          count('school.fee', [('state','=','paid')])),
        ("  └ Partial",       count('school.fee', [('state','=','partial')])),
        ("  └ Overdue",       count('school.fee', [('state','=','overdue')])),
        ("Payments",          count('school.fee.payment')),
        ("Attendance records",count('school.attendance')),
        ("Exams",             count('school.exam')),
        ("Grades",            count('school.grade')),
        ("Timetables",        count('school.timetable')),
        ("Timetable slots",   count('school.timetable.slot')),
        ("Announcements",     count('school.announcement')),
    ]
    for label, value in rows:
        print(f"  {label:<24} {value:>5}")

    print("=" * 64)
    print("  URL   :  http://localhost:8069")
    print("  DB    :  demo")
    print("  Login :  admin / admin")
    print("=" * 64)

    # =========================================================================
    # 14. Create user accounts
    # =========================================================================
    section = lambda n, t, title: print(f"\n[{n}/{t}] {title}\n  {'─' * 50}")
    section(14, 14, "User Accounts")

    def make_user(login, name, email, groups_xmlids):
        existing = env['res.users'].search([('login', '=', login)], limit=1)
        if existing:
            return existing, False
        user = env['res.users'].with_context(no_reset_password=True).create({
            'name':     name,
            'login':    login,
            'email':    email,
            'password': 'School@2026',
        })
        for xmlid in groups_xmlids:
            try:
                grp = env.ref(xmlid)
                grp.write({'users': [(4, user.id)]})
            except Exception:
                pass
        return user, True

    G = {
        'admin':      'school_management.group_school_admin',
        'principal':  'school_management.group_school_principal',
        'affairs':    'school_management.group_school_affairs',
        'accountant': 'school_management.group_school_accountant',
        'teacher':    'school_management.group_school_teacher',
        'student':    'school_management.group_school_student',
        'parent':     'school_management.group_school_parent',
    }

    users_created = 0
    u, c = make_user('ahmed.rashidi@school.sa', 'أحمد الرشيدي',  'ahmed.rashidi@school.sa',  [G['principal']])
    users_created += c
    u, c = make_user('affairs@school.sa',        'شؤون الطلاب',   'affairs@school.sa',         [G['affairs']])
    users_created += c
    u, c = make_user('accountant@school.sa',     'المحاسب',        'accountant@school.sa',      [G['accountant']])
    users_created += c

    for login, name in [
        ('fatima.zahrani@school.sa',        'فاطمة الزهراني'),
        ('omar.ghamdi@school.sa',           'عمر الغامدي'),
        ('maryam.otaibi@school.sa',         'مريم العتيبي'),
        ('khalid.dosari@school.sa',         'خالد الدوسري'),
        ('sara.shehri@school.sa',           'سارة الشهري'),
        ('hassan.harbi@school.sa',          'حسن الحربي'),
        ('wafa.balawi@school.sa',           'وفاء البلوي'),
        ('nasser.shammari@northcampus.sa',  'ناصر الشمري'),
    ]:
        u, c = make_user(login, name, login, [G['teacher']])
        users_created += c

    for g in env['school.guardian'].search([]):
        if g.email:
            u, c = make_user(g.email, g.name, g.email, [G['parent']])
            users_created += c

    for s in env['school.student'].search([]):
        first = s.name.split()[0]
        login = f"{first}.{s.student_code}@student.sa"
        u, c = make_user(login, s.name, login, [G['student']])
        users_created += c

    cr.commit()
    print(f"  → {users_created} user accounts created")

PYEOF

# ---------------------------------------------------------------------------
# 6. Install Arabic language + load translations
# ---------------------------------------------------------------------------
info "Installing Arabic language (ar_001)..."
docker exec "$ODOO_CONTAINER" odoo \
    -c /etc/odoo/odoo.conf \
    -d "$DB" \
    --load-language=ar_001 \
    --stop-after-init

info "Loading Arabic translations (upgrading module)..."
docker exec "$ODOO_CONTAINER" odoo \
    -c /etc/odoo/odoo.conf \
    -d "$DB" \
    --update=school_management \
    --stop-after-init

info "Setting Arabic as default language for all users..."
docker exec "$DB_CONTAINER" psql -U "$DB_USER" -d "$DB" \
    -c "UPDATE res_partner SET lang = 'ar_001'
        WHERE id IN (SELECT partner_id FROM res_users WHERE active = TRUE);"

info "Demo database setup complete."
info "URL: http://$(hostname -I | awk '{print $1}'):8069  |  admin / admin  |  Language: العربية"
