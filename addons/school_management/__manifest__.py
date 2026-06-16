# -*- coding: utf-8 -*-
{
    'name': 'School Management System',
    'version': '17.0.8.0.0',
    'category': 'Education',
    'summary': 'Comprehensive School Management System for Odoo 17',
    'description': """
        School Management System
        ========================
        A complete school management solution including:
        - Student registration and management
        - Teacher management
        - Classroom and academic year management
        - Attendance tracking
        - Grades and exams
        - Fee management with accounting integration
        - Parent portal
        - QWeb PDF reports and certificates
    """,
    'author': 'School Management',
    'website': '',
    'license': 'LGPL-3',
    'depends': [
        'base',
        'mail',
        'account',
        'web',
        'portal',
        'website',
    ],
    'data': [
        # Security
        'security/security_groups.xml',
        'security/ir.model.access.csv',
        'security/record_rules.xml',
        # Data
        'data/sequence_data.xml',
        'data/fee_type_data.xml',
        'data/email_templates.xml',
        'data/dashboard_data.xml',
        'data/period_data.xml',
        'data/communication_templates.xml',
        'data/school_branch_data.xml',
        'data/enrollment_requirements_data.xml',
        # Report QWeb templates (before views so actions are available)
        'report/report_timetable.xml',
        'report/report_grade_sheet.xml',
        'report/report_attendance.xml',
        'report/report_fee_statement.xml',
        'report/report_receipt.xml',
        'report/report_certificates.xml',
        # Report actions (must load before views that reference them)
        'report/report_actions.xml',
        # Views - Phase 1
        'views/academic_year_views.xml',
        'views/student_views.xml',
        'views/teacher_views.xml',
        'views/class_views.xml',
        # Views - Phase 2
        'views/attendance_views.xml',
        'views/exam_views.xml',
        'views/grade_views.xml',
        # Views - Phase 3
        'views/fee_views.xml',
        'views/portal/portal_templates.xml',
        # Views - Phase 5 (Dashboard & Analytics)
        'views/analysis_views.xml',
        'views/dashboard_views.xml',
        # Views - Phase 6 (Timetable)
        'views/timetable_views.xml',
        # Views - Phase 7 (Communication)
        'views/communication_views.xml',
        'views/portal/announcement_templates.xml',
        # Views - Phase 8 (Multi-school)
        'views/school_branch_views.xml',
        # Views - Enrollment & Installments
        'views/enrollment_views.xml',
        # Menus (always last)
        'views/menu_views.xml',
        # Hide unneeded built-in menus
        'data/hide_menus.xml',
    ],
    'demo': [],
    'installable': True,
    'auto_install': False,
    'application': True,
    'sequence': 1,
}
