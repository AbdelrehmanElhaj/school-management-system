# -*- coding: utf-8 -*-
import base64
import io
from odoo import models, fields, api, _


def _generate_qr_image(data):
    try:
        import qrcode
        qr = qrcode.QRCode(version=1, box_size=8, border=2)
        qr.add_data(data)
        qr.make(fit=True)
        img = qr.make_image(fill_color='black', back_color='white')
        buf = io.BytesIO()
        img.save(buf, format='PNG')
        return base64.b64encode(buf.getvalue())
    except Exception:
        return False


class StudentQr(models.Model):
    _inherit = 'school.student'

    qr_code = fields.Char(
        string='QR Code', copy=False, index=True,
        help='Unique identifier encoded in this student\'s QR code'
    )
    qr_code_image = fields.Binary(
        string='QR Code Image', compute='_compute_qr_code_image'
    )

    _sql_constraints = [
        ('qr_code_unique', 'UNIQUE(qr_code)', 'QR code must be unique per student.'),
    ]

    @api.model_create_multi
    def create(self, vals_list):
        records = super().create(vals_list)
        for rec in records:
            if not rec.qr_code:
                rec.qr_code = f"STU-{rec.id:05d}"
        return records

    @api.depends('qr_code')
    def _compute_qr_code_image(self):
        for rec in self:
            if rec.qr_code:
                rec.qr_code_image = _generate_qr_image(f"STUDENT:{rec.qr_code}")
            else:
                rec.qr_code_image = False

    def action_print_qr_card(self):
        return self.env.ref(
            'school_qr_attendance.action_report_student_qr_card'
        ).report_action(self)


class TeacherQr(models.Model):
    _inherit = 'school.teacher'

    qr_code = fields.Char(
        string='QR Code', copy=False, index=True,
        help='Unique identifier encoded in this teacher\'s QR code'
    )
    qr_code_image = fields.Binary(
        string='QR Code Image', compute='_compute_qr_code_image'
    )

    _sql_constraints = [
        ('qr_code_unique', 'UNIQUE(qr_code)', 'QR code must be unique per teacher.'),
    ]

    @api.model_create_multi
    def create(self, vals_list):
        records = super().create(vals_list)
        for rec in records:
            if not rec.qr_code:
                rec.qr_code = f"TCH-{rec.id:05d}"
        return records

    @api.depends('qr_code')
    def _compute_qr_code_image(self):
        for rec in self:
            if rec.qr_code:
                rec.qr_code_image = _generate_qr_image(f"TEACHER:{rec.qr_code}")
            else:
                rec.qr_code_image = False

    def action_print_qr_card(self):
        return self.env.ref(
            'school_qr_attendance.action_report_teacher_qr_card'
        ).report_action(self)


class AttendanceQr(models.Model):
    _inherit = 'school.attendance'

    qr_session_id = fields.Many2one(
        'school.qr.session', string='QR Session', ondelete='set null'
    )
    source = fields.Selection([
        ('qr', 'QR Code'),
        ('manual', 'Manual'),
    ], string='Source', default='manual')
