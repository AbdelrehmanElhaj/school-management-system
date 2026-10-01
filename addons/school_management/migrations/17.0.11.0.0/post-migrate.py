# -*- coding: utf-8 -*-
"""WP3 post-migration: seed the 2026-2027 fee matrix.

Done in a migration (not XML data) so an academic year the school already
created by hand is reused instead of duplicated. Idempotent: existing
structure rows are kept. KG amounts are a pending client decision and are
intentionally not seeded.
"""
import logging

from odoo import api, SUPERUSER_ID

_logger = logging.getLogger(__name__)

TUITION_AMOUNTS = {
    'grade1': 9000, 'grade2': 9000, 'grade3': 9000, 'grade4': 9000,
    'grade5': 9000,
    'grade6': 12000, 'grade7': 12000, 'grade8': 12000, 'grade9': 12000,
    'grade10': 12000, 'grade11': 12000, 'grade12': 12000,
}
FORM_AMOUNT = 250
REGISTRATION_AMOUNT = 2000


def migrate(cr, version):
    env = api.Environment(cr, SUPERUSER_ID, {})
    Year = env['school.academic.year']
    year = Year.search(['|', ('code', '=', '2026-2027'),
                        ('name', 'ilike', '2026-2027')], limit=1)
    if not year:
        year = Year.create({
            'name': '2026-2027',
            'code': '2026-2027',
            'date_start': '2026-09-01',
            'date_end': '2027-06-30',
        })
        _logger.info('WP3 migration: created draft academic year 2026-2027.')
    Structure = env['school.fee.structure']
    tuition = env.ref('school_management.fee_type_tuition',
                      raise_if_not_found=False)
    registration = env.ref('school_management.fee_type_registration',
                           raise_if_not_found=False)
    form = env.ref('school_management.fee_type_form',
                   raise_if_not_found=False)
    existing = Structure.with_context(active_test=False).search([
        ('academic_year_id', '=', year.id)])
    keys = {(s.grade_level, s.fee_type_id.id, s.term) for s in existing}
    vals = []
    for grade in TUITION_AMOUNTS:
        if tuition and (grade, tuition.id, 'annual') not in keys:
            vals.append({'academic_year_id': year.id, 'grade_level': grade,
                         'fee_type_id': tuition.id, 'term': 'annual',
                         'amount': TUITION_AMOUNTS[grade]})
        if form and (grade, form.id, 'annual') not in keys:
            vals.append({'academic_year_id': year.id, 'grade_level': grade,
                         'fee_type_id': form.id, 'term': 'annual',
                         'amount': FORM_AMOUNT})
        if registration and (grade, registration.id, 'annual') not in keys:
            vals.append({'academic_year_id': year.id, 'grade_level': grade,
                         'fee_type_id': registration.id, 'term': 'annual',
                         'amount': REGISTRATION_AMOUNT})
    Structure.create(vals)
    _logger.info('WP3 migration: seeded %d fee structure rows for %s.',
                 len(vals), year.name)
