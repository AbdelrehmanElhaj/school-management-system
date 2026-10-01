# -*- coding: utf-8 -*-
"""WP1 post-migration: backfill yearly enrollment records.

Creates one school.student.enrollment per enrolled student for the academic
year of his current class, so the history is complete before the first
promotion to 2026-2027 runs.
"""
import logging

from odoo import api, SUPERUSER_ID

_logger = logging.getLogger(__name__)

STATUS_TO_STATE = {
    'active': 'enrolled',
    'paused': 'enrolled',
    'withdrawn': 'withdrawn',
    'transferred': 'withdrawn',
    'graduated': 'graduated',
}


def migrate(cr, version):
    env = api.Environment(cr, SUPERUSER_ID, {})
    Enrollment = env['school.student.enrollment']
    students = env['school.student'].search([
        ('class_id', '!=', False),
        ('enrollment_state', '=', 'active'),
    ])
    created = 0
    for student in students:
        year = student.class_id.academic_year_id
        if not year:
            continue
        if Enrollment.search_count([
            ('student_id', '=', student.id),
            ('academic_year_id', '=', year.id),
        ]):
            continue
        Enrollment.create({
            'student_id': student.id,
            'academic_year_id': year.id,
            'class_id': student.class_id.id,
            'grade_level': student.class_id.grade_level,
            'state': STATUS_TO_STATE.get(student.status, 'enrolled'),
            'enrollment_date': student.enrollment_date,
        })
        created += 1
    _logger.info(
        'WP1 migration: created %d enrollment records for %d students.',
        created, len(students))
