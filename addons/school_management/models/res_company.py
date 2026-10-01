# -*- coding: utf-8 -*-
from odoo import models, fields


class ResCompany(models.Model):
    _inherit = 'res.company'

    # Branding (logo, primary_color and secondary_color already exist on
    # res.company and are reused by the unified report layout in WP4).
    school_name_en = fields.Char(
        string='School Name (English)',
        help='Shown alongside the Arabic company name on bilingual documents.'
    )
    school_license_no = fields.Char(
        string='License / Registry No.',
        help='Ministry registration or license number printed on documents.'
    )

    # Registration settings
    enrollment_require_docs = fields.Boolean(
        string='Require Complete Documents Before Approval', default=True,
        help='Block enrollment approval while required checklist documents '
             'are still pending.'
    )
    target_student_count = fields.Integer(
        string='Target Student Count',
        help='Enrollment target for the active year (dashboard card).'
    )

    # Billing settings
    registration_fee_deduction = fields.Boolean(
        string='Deduct Registration Fee From Tuition', default=True,
        help='A paid registration fee becomes a credit on the tuition fee '
             'generated at approval.'
    )
    receipt_footer_text = fields.Text(
        string='Receipt / Invoice Footer Text',
        help='Printed at the bottom of receipts, invoices and claims.'
    )
