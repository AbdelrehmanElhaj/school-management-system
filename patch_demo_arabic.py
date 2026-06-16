#!/usr/bin/env python3
"""
Patch setup_demo_data.sh: replace all English names with Arabic script names.
"""

import re

with open("setup_demo_data.sh", encoding="utf-8") as f:
    src = f.read()

REPLACEMENTS = [
    # ── School branches ────────────────────────────────────────────────────
    ("'name':    'Main Campus'", "'name':    'المدرسة الرئيسية'"),
    ("'name':    'North Campus'", "'name':    'الحرم الشمالي'"),
    ("ok(f\"Main Campus  (code: MAIN)\", c)", "ok(f\"المدرسة الرئيسية  (code: MAIN)\", c)"),
    ("ok(f\"North Campus (code: NORTH)\", c)", "ok(f\"الحرم الشمالي (code: NORTH)\", c)"),

    # ── Academic years ─────────────────────────────────────────────────────
    ("'name':       'Academic Year 2024-2025'",    "'name':       'السنة الدراسية 2024-2025'"),
    ("'name':       'Academic Year 2025-2026'",    "'name':       'السنة الدراسية 2025-2026'"),
    ("'name':       'Academic Year 2025-2026 — North'", "'name':       'السنة الدراسية 2025-2026 — الشمالي'"),
    ('ok("2024-2025  Main Campus  (done)", c)',    'ok("2024-2025  المدرسة الرئيسية  (منتهي)", c)'),
    ('ok("2025-2026  Main Campus  (active / current)", c)', 'ok("2025-2026  المدرسة الرئيسية  (نشط / حالي)", c)'),
    ('ok("2025-2026-N North Campus (active)", c)', 'ok("2025-2026-N الحرم الشمالي (نشط)", c)'),

    # ── Teachers ───────────────────────────────────────────────────────────
    ("('Ahmed Al-Rashidi',   'ahmed.rashidi@school.sa'",
     "('أحمد الرشيدي',   'ahmed.rashidi@school.sa'"),
    ("('Fatima Al-Zahrani',  'fatima.zahrani@school.sa'",
     "('فاطمة الزهراني',  'fatima.zahrani@school.sa'"),
    ("('Omar Al-Ghamdi',     'omar.ghamdi@school.sa'",
     "('عمر الغامدي',     'omar.ghamdi@school.sa'"),
    ("('Maryam Al-Otaibi',   'maryam.otaibi@school.sa'",
     "('مريم العتيبي',   'maryam.otaibi@school.sa'"),
    ("('Khalid Al-Dosari',   'khalid.dosari@school.sa'",
     "('خالد الدوسري',   'khalid.dosari@school.sa'"),
    ("('Sara Al-Shehri',     'sara.shehri@school.sa'",
     "('سارة الشهري',     'sara.shehri@school.sa'"),
    ("('Hassan Al-Harbi',    'hassan.harbi@school.sa'",
     "('حسن الحربي',    'hassan.harbi@school.sa'"),
    ("('Wafa Al-Balawi',     'wafa.balawi@school.sa'",
     "('وفاء البلوي',     'wafa.balawi@school.sa'"),
    ("('Nasser Al-Shammari', 'nasser.shammari@northcampus.sa'",
     "('ناصر الشمري', 'nasser.shammari@northcampus.sa'"),

    # teacher dict lookups
    ("ahmed   = teachers['Ahmed Al-Rashidi']",   "ahmed   = teachers['أحمد الرشيدي']"),
    ("fatima  = teachers['Fatima Al-Zahrani']",  "fatima  = teachers['فاطمة الزهراني']"),
    ("omar    = teachers['Omar Al-Ghamdi']",     "omar    = teachers['عمر الغامدي']"),
    ("maryam  = teachers['Maryam Al-Otaibi']",  "maryam  = teachers['مريم العتيبي']"),
    ("khalid  = teachers['Khalid Al-Dosari']",  "khalid  = teachers['خالد الدوسري']"),
    ("sara    = teachers['Sara Al-Shehri']",    "sara    = teachers['سارة الشهري']"),
    ("hassan  = teachers['Hassan Al-Harbi']",   "hassan  = teachers['حسن الحربي']"),
    ("wafa    = teachers['Wafa Al-Balawi']",    "wafa    = teachers['وفاء البلوي']"),
    ("nasser  = teachers['Nasser Al-Shammari']","nasser  = teachers['ناصر الشمري']"),

    # qualification (keep English - it's just content, not a person name)
    # (skipped)

    # ── Guardians ──────────────────────────────────────────────────────────
    ("('Abdullah Al-Harbi',    'father'", "('عبدالله الحربي',    'father'"),
    ("('Nora Al-Harbi',        'mother'", "('نورة الحربي',        'mother'"),
    ("('Mohammed Al-Qahtani',  'father'", "('محمد القحطاني',  'father'"),
    ("('Hessa Al-Shammari',    'mother'", "('حصة الشمري',    'mother'"),
    ("('Saad Al-Mutairi',      'father'", "('سعد المطيري',      'father'"),
    ("('Reem Al-Anazi',        'mother'", "('ريم العنزي',        'mother'"),
    ("('Ibrahim Al-Sulami',    'father'", "('إبراهيم السلمي',    'father'"),
    ("('Manal Al-Ghamdi',      'mother'", "('منال الغامدي',      'mother'"),
    ("('Turki Al-Zahrani',     'father'", "('تركي الزهراني',     'father'"),
    ("('Dalal Al-Otaibi',      'mother'", "('دلال العتيبي',      'mother'"),
    ("('Fawaz Al-Enezi',       'father'", "('فواز العنزي',       'father'"),
    ("('Samira Al-Bishi',      'mother'", "('سميرة البيشي',      'mother'"),
    ("('Waleed Al-Dossari',    'father'", "('وليد الدوسري',    'father'"),
    ("('Layla Al-Hamdan',      'mother'", "('ليلى الحمدان',      'mother'"),
    ("('Salman Al-Rashidi',    'father'", "('سلمان الرشيدي',    'father'"),
    ("('Widad Al-Subaie',      'mother'", "('وداد السبيعي',      'mother'"),
    ("('Naif Al-Maliki',       'father'", "('نايف المالكي',       'father'"),
    ("('Ghada Al-Thubaiti',    'mother'", "('غادة الثبيتي',    'mother'"),
    ("('Meshal Al-Faifi',      'father'", "('مشعل الفيفي',      'father'"),
    ("('Haifa Al-Yami',        'mother'", "('هيفاء اليامي',        'mother'"),
    ("('Rashid Al-Shahrani',   'father'", "('راشد الشهراني',   'father'"),
    ("('Mariam Al-Khalidi',    'mother'", "('مريم الخالدي',    'mother'"),
    ("('Abdulrahman Al-Aqeel', 'father'", "('عبدالرحمن العقيل', 'father'"),
    ("('Suniya Al-Aqeel',      'mother'", "('سنية العقيل',      'mother'"),
    ("('Majed Al-Shalan',      'father'", "('ماجد الشلاّن',      'father'"),
    ("('Hind Al-Shalan',       'mother'", "('هند الشلاّن',       'mother'"),
    ("('Faris Al-Duweesh',     'father'", "('فارس الدويش',     'father'"),
    ("('Sara Al-Johani',       'mother'", "('سارة الجهني',       'mother'"),

    # ── Students — Main campus ─────────────────────────────────────────────
    ("('Ali Abdullah Al-Harbi',",      "('علي عبدالله الحربي',"),
    ("('Lina Mohammed Al-Qahtani',",   "('لينا محمد القحطاني',"),
    ("('Omar Saad Al-Mutairi',",       "('عمر سعد المطيري',"),
    ("('Nada Ibrahim Al-Sulami',",     "('ندى إبراهيم السلمي',"),
    ("('Youssef Turki Al-Zahrani',",   "('يوسف تركي الزهراني',"),
    ("('Haya Fawaz Al-Enezi',",        "('هيا فواز العنزي',"),
    ("('Faisal Waleed Al-Dossari',",   "('فيصل وليد الدوسري',"),
    ("('Ghaida Salman Al-Rashidi',",   "('غيداء سلمان الرشيدي',"),
    ("('Rayan Naif Al-Maliki',",       "('ريان نايف المالكي',"),
    ("('Sara Meshal Al-Faifi',",       "('سارة مشعل الفيفي',"),
    ("('Majed Rashid Al-Shahrani',",   "('ماجد راشد الشهراني',"),
    ("('Arwa Abdullah Al-Harbi',",     "('أروى عبدالله الحربي',"),
    ("('Khalid Mohammed Al-Qahtani',", "('خالد محمد القحطاني',"),
    ("('Dana Saad Al-Mutairi',",       "('دانة سعد المطيري',"),
    ("('Bandar Ibrahim Al-Sulami',",   "('بندر إبراهيم السلمي',"),
    ("('Rand Turki Al-Zahrani',",      "('رند تركي الزهراني',"),
    ("('Nawaf Fawaz Al-Enezi',",       "('نواف فواز العنزي',"),
    ("('Ghala Waleed Al-Dossari',",    "('غلا وليد الدوسري',"),
    ("('Saud Salman Al-Rashidi',",     "('سعود سلمان الرشيدي',"),
    ("('Lujain Naif Al-Maliki',",      "('لجين نايف المالكي',"),
    ("('Badr Meshal Al-Faifi',",       "('بدر مشعل الفيفي',"),
    ("('Reema Rashid Al-Shahrani',",   "('ريما راشد الشهراني',"),
    ("('Sultan Abdullah Al-Harbi',",   "('سلطان عبدالله الحربي',"),
    ("('Fatima Mohammed Al-Qahtani',", "('فاطمة محمد القحطاني',"),
    ("('Nayef Saad Al-Mutairi',",      "('نايف سعد المطيري',"),
    ("('Dima Ibrahim Al-Sulami',",     "('ديمة إبراهيم السلمي',"),
    ("('Hamad Turki Al-Zahrani',",     "('حمد تركي الزهراني',"),
    ("('Maha Fawaz Al-Enezi',",        "('مها فواز العنزي',"),
    ("('Tariq Waleed Al-Dossari',",    "('طارق وليد الدوسري',"),
    ("('Hind Salman Al-Rashidi',",     "('هند سلمان الرشيدي',"),
    ("('Osama Naif Al-Maliki',",       "('أسامة نايف المالكي',"),
    ("('Asma Meshal Al-Faifi',",       "('أسماء مشعل الفيفي',"),
    ("('Yazeed Rashid Al-Shahrani',",  "('يزيد راشد الشهراني',"),
    ("('Abrar Abdullah Al-Harbi',",    "('أبرار عبدالله الحربي',"),
    ("('Rashed Mohammed Al-Qahtani',", "('راشد محمد القحطاني',"),
    ("('Layla Saad Al-Mutairi',",      "('ليلى سعد المطيري',"),
    ("('Mishal Ibrahim Al-Sulami',",   "('مشعل إبراهيم السلمي',"),
    ("('Tahani Turki Al-Zahrani',",    "('تهاني تركي الزهراني',"),
    ("('Feras Fawaz Al-Enezi',",       "('فراس فواز العنزي',"),

    # ── Students — North campus ────────────────────────────────────────────
    ("('Noor Abdulrahman Al-Aqeel',",   "('نور عبدالرحمن العقيل',"),
    ("('Tariq Majed Al-Shalan',",       "('طارق ماجد الشلاّن',"),
    ("('Rima Faris Al-Duweesh',",       "('ريما فارس الدويش',"),
    ("('Khaled Abdulrahman Al-Aqeel',", "('خالد عبدالرحمن العقيل',"),
    ("('Dina Majed Al-Shalan',",        "('دينا ماجد الشلاّن',"),
    ("('Sami Faris Al-Duweesh',",       "('سامي فارس الدويش',"),

    # ── Announcements ─────────────────────────────────────────────────────
    ("'name': 'Welcome Back — New Academic Year 2025-2026'",
     "'name': 'أهلاً بالعودة — السنة الدراسية الجديدة 2025-2026'"),
    ("'name': 'Exam Schedule — First Term 2025'",
     "'name': 'جدول الاختبارات — الفصل الأول 2025'"),
    ("'name': 'School Fee Payment Reminder — Term 2'",
     "'name': 'تذكير سداد الرسوم المدرسية — الفصل الثاني'"),
    ("'name': 'Parent-Teacher Meeting — December 10, 2025'",
     "'name': 'اجتماع أولياء الأمور والمعلمين — 10 ديسمبر 2025'"),
]

for old, new in REPLACEMENTS:
    if old not in src:
        print(f"WARNING: not found: {repr(old[:60])}")
    else:
        src = src.replace(old, new, 1)

# ── Announcement body translations ────────────────────────────────────────────
old_bodies = [
    (
        "'body':         '<p>Dear Students and Parents,</p>"
        "<p>We are delighted to welcome you back for the <strong>2025-2026 Academic Year</strong>.</p>"
        "<p>Classes begin on <strong>September 1, 2025</strong>. "
        "Please ensure all registration documents are submitted to the school office by August 25.</p>'",
        "'body':         '<p>أعزاءنا الطلاب وأولياء الأمور،</p>"
        "<p>يسعدنا الترحيب بكم في بداية <strong>العام الدراسي 2025-2026</strong>.</p>"
        "<p>تبدأ الدراسة في <strong>1 سبتمبر 2025</strong>. "
        "يرجى التأكد من تسليم جميع وثائق التسجيل لمكتب المدرسة قبل 25 أغسطس.</p>'"
    ),
    (
        "'body':         '<p>The first-term examination schedule has been finalized.</p>"
        "<p>Exams will be held from <strong>November 15 – November 30, 2025</strong>. "
        "Students are advised to review all subjects. Good luck!</p>'",
        "'body':         '<p>تم الإعلان عن جدول اختبارات الفصل الأول.</p>"
        "<p>تُعقد الاختبارات من <strong>15 إلى 30 نوفمبر 2025</strong>. "
        "ننصح الطلاب بمراجعة جميع المواد. حظاً موفقاً!</p>'"
    ),
    (
        "'body':         '<p>This is a reminder that the <strong>Second Term fee payment deadline</strong> "
        "is <strong>January 15, 2026</strong>.</p>"
        "<p>Please log in to the parent portal or contact the accounting office to settle your balance.</p>'",
        "'body':         '<p>تذكير بأن الموعد النهائي لسداد <strong>رسوم الفصل الثاني</strong> "
        "هو <strong>15 يناير 2026</strong>.</p>"
        "<p>يرجى تسجيل الدخول إلى بوابة ولي الأمر أو التواصل مع قسم الحسابات لتسوية الرصيد.</p>'"
    ),
    (
        "'body':         '<p>We invite all parents to attend the <strong>Parent-Teacher Meeting</strong> "
        "on Wednesday, 10 December 2025.</p>'"
        "<p>Timings: 4:00 PM – 7:00 PM. Please book your appointment through the school office.</p>'",
        "'body':         '<p>ندعو جميع أولياء الأمور لحضور <strong>اجتماع أولياء الأمور والمعلمين</strong> "
        "يوم الأربعاء 10 ديسمبر 2025.</p>'"
        "<p>المواعيد: 4:00 م – 7:00 م. يرجى حجز موعدكم عبر مكتب المدرسة.</p>'"
    ),
]

for old_body, new_body in old_bodies:
    if old_body in src:
        src = src.replace(old_body, new_body, 1)

# ── Append language + user creation section before final PYEOF ────────────────
USER_SECTION = '''
    # =========================================================================
    # 14. Install Arabic language & create users
    # =========================================================================
    section = lambda n, t, title: print(f"\\n[{n}/{t}] {title}\\n  {'─' * 50}")
    section(14, 14, "Arabic Language & User Accounts")

    # Activate Arabic language
    ar_lang = env['res.lang'].search([('code', '=', 'ar_001')], limit=1)
    if ar_lang and not ar_lang.active:
        ar_lang.write({'active': True})
    print("  Arabic (ar_001) language: active")

    # Helper to create user
    def make_user(login, name, email, groups_xmlids, lang='ar_001'):
        existing = env['res.users'].search([('login', '=', login)], limit=1)
        if existing:
            existing.partner_id.write({'lang': lang})
            return existing, False
        user = env['res.users'].with_context(no_reset_password=True).create({
            'name':     name,
            'login':    login,
            'email':    email,
            'password': 'School@2026',
        })
        user.partner_id.write({'lang': lang})
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
    # Principal
    u, c = make_user('ahmed.rashidi@school.sa', 'أحمد الرشيدي', 'ahmed.rashidi@school.sa', [G['principal']])
    users_created += c

    # Affairs
    u, c = make_user('affairs@school.sa', 'شؤون الطلاب', 'affairs@school.sa', [G['affairs']])
    users_created += c

    # Accountant
    u, c = make_user('accountant@school.sa', 'المحاسب', 'accountant@school.sa', [G['accountant']])
    users_created += c

    # Teachers
    teacher_logins = [
        ('fatima.zahrani@school.sa',    'فاطمة الزهراني'),
        ('omar.ghamdi@school.sa',       'عمر الغامدي'),
        ('maryam.otaibi@school.sa',     'مريم العتيبي'),
        ('khalid.dosari@school.sa',     'خالد الدوسري'),
        ('sara.shehri@school.sa',       'سارة الشهري'),
        ('hassan.harbi@school.sa',      'حسن الحربي'),
        ('wafa.balawi@school.sa',       'وفاء البلوي'),
        ('nasser.shammari@northcampus.sa', 'ناصر الشمري'),
    ]
    for login, name in teacher_logins:
        u, c = make_user(login, name, login, [G['teacher']])
        users_created += c

    # Guardian users
    guardians_all = env['school.guardian'].search([])
    for g in guardians_all:
        if g.email:
            login = g.email
            u, c = make_user(login, g.name, login, [G['parent']])
            users_created += c

    # Student users
    students_all = env['school.student'].search([])
    for s in students_all:
        first = s.name.split()[0]
        login = f"{first}.{s.student_code}@student.sa"
        u, c = make_user(login, s.name, login, [G['student']])
        users_created += c

    # Set Arabic language on ALL user partners
    all_users = env['res.users'].search([('active', '=', True)])
    all_users.mapped('partner_id').write({'lang': 'ar_001'})

    cr.commit()
    print(f"  → {users_created} new users created")
    print(f"  → {len(all_users)} users set to Arabic (ar_001)")

'''

src = src.replace(
    '\nPYEOF\n',
    USER_SECTION + '\nPYEOF\n',
    1
)

with open("setup_demo_data.sh", "w", encoding="utf-8") as f:
    f.write(src)

print("Patched setup_demo_data.sh successfully")
print("Run: bash setup_demo_data.sh")
