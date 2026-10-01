# -*- coding: utf-8 -*-
from odoo import models, fields


class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    school_name_en = fields.Char(
        related='company_id.school_name_en', readonly=False
    )
    school_license_no = fields.Char(
        related='company_id.school_license_no', readonly=False
    )
    company_logo = fields.Binary(
        related='company_id.logo', readonly=False, string='School Logo'
    )
    company_primary_color = fields.Char(
        related='company_id.primary_color', readonly=False,
        string='Primary Color'
    )
    company_secondary_color = fields.Char(
        related='company_id.secondary_color', readonly=False,
        string='Secondary Color'
    )
    enrollment_require_docs = fields.Boolean(
        related='company_id.enrollment_require_docs', readonly=False
    )
    target_student_count = fields.Integer(
        related='company_id.target_student_count', readonly=False
    )
    registration_fee_deduction = fields.Boolean(
        related='company_id.registration_fee_deduction', readonly=False
    )
    receipt_footer_text = fields.Text(
        related='company_id.receipt_footer_text', readonly=False
    )
