# -*- coding: utf-8 -*-
from odoo import models, fields, _


class StudentRejectWizard(models.TransientModel):
    _name = 'school.student.reject.wizard'
    _description = 'Reject Enrollment Application'

    student_ids = fields.Many2many(
        'school.student', string='الطلاب', required=True
    )
    reason = fields.Char(string='سبب الرفض', required=True)

    def action_reject(self):
        self.ensure_one()
        self.student_ids._check_approver_rights()
        for student in self.student_ids.filtered(
                lambda s: s.enrollment_state == 'pending_approval'):
            student.write({
                'enrollment_state': 'rejected',
                'rejection_reason': self.reason,
            })
            student.message_post(body=_(
                'رُفض طلب التسجيل — السبب: %s') % self.reason)
        return {'type': 'ir.actions.act_window_close'}
