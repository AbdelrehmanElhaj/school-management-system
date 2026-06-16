# -*- coding: utf-8 -*-
{
    'name': 'School QR Attendance',
    'version': '17.0.1.0.0',
    'summary': 'Kiosk-based QR code attendance for students and teachers',
    'author': 'School Management',
    'category': 'Education',
    'depends': ['school_management', 'web'],
    'data': [
        'security/ir.model.access.csv',
        'views/qr_session_views.xml',
        'views/teacher_attendance_views.xml',
        'views/student_qr_views.xml',
        'views/teacher_qr_views.xml',
        'views/menu_views.xml',
        'report/student_qr_card.xml',
        'report/teacher_qr_card.xml',
    ],
    'assets': {
        'web.assets_frontend': [
            'school_qr_attendance/static/src/js/jsQR.min.js',
        ],
    },
    'installable': True,
    'application': False,
    'license': 'LGPL-3',
}
