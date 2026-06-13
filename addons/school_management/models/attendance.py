# -*- coding: utf-8 -*-
from odoo import models, fields, api, _
from odoo.exceptions import ValidationError


class Attendance(models.Model):
    _name = 'school.attendance'
    _description = 'Student Attendance'
    _inherit = ['mail.thread']
    _order = 'date desc, class_id, student_id'
    _rec_name = 'display_name'

    display_name = fields.Char(
        string='Reference', compute='_compute_display_name', store=True
    )
    student_id = fields.Many2one(
        'school.student', string='Student', required=True,
        domain=[('status', '=', 'active')], tracking=True
    )
    class_id = fields.Many2one(
        'school.class', string='Class', required=True, tracking=True
    )
    academic_year_id = fields.Many2one(
        'school.academic.year', string='Academic Year',
        related='class_id.academic_year_id', store=True
    )
    school_id = fields.Many2one(
        'school.branch', string='School',
        related='class_id.school_id', store=True
    )
    date = fields.Date(
        string='Date', required=True, default=fields.Date.today, tracking=True
    )
    status = fields.Selection([
        ('present', 'Present'),
        ('absent', 'Absent'),
        ('late', 'Late'),
        ('excused', 'Excused'),
    ], string='Status', required=True, default='present', tracking=True)
    teacher_id = fields.Many2one(
        'school.teacher', string='Recorded By', tracking=True
    )
    notes = fields.Text(string='Notes')

    _sql_constraints = [
        ('student_date_unique', 'UNIQUE(student_id, date)',
         'Attendance record already exists for this student on this date.'),
    ]

    @api.depends('student_id', 'date')
    def _compute_display_name(self):
        for rec in self:
            student = rec.student_id.name or ''
            date = str(rec.date) if rec.date else ''
            rec.display_name = f"{student} / {date}" if student and date else student or date

    @api.onchange('student_id')
    def _onchange_student(self):
        if self.student_id and self.student_id.class_id:
            self.class_id = self.student_id.class_id

    @api.constrains('date')
    def _check_date(self):
        from datetime import date
        for rec in self:
            if rec.date and rec.date > date.today():
                raise ValidationError(_('Attendance date cannot be in the future.'))

    def action_send_absence_alert(self):
        template = self.env.ref(
            'school_management.email_template_absence_alert',
            raise_if_not_found=False,
        )
        if not template:
            raise ValidationError(_('Absence alert email template not found.'))
        sent = 0
        for rec in self.filtered(lambda a: a.status == 'absent'):
            if rec.student_id.guardian_id.email:
                template.send_mail(rec.id, force_send=True)
                sent += 1
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'message': _('Absence alert sent to %d guardian(s).') % sent,
                'type': 'success' if sent else 'warning',
                'sticky': False,
            }
        }


class AttendanceBulk(models.TransientModel):
    """Wizard to record attendance for a whole class at once."""
    _name = 'school.attendance.bulk'
    _description = 'Bulk Attendance Wizard'

    class_id = fields.Many2one('school.class', string='Class', required=True)
    date = fields.Date(string='Date', required=True, default=fields.Date.today)
    line_ids = fields.One2many(
        'school.attendance.bulk.line', 'wizard_id', string='Students'
    )

    @api.onchange('class_id')
    def _onchange_class(self):
        if self.class_id:
            lines = [(5, 0, 0)]
            for student in self.class_id.student_ids.filtered(lambda s: s.status == 'active'):
                lines.append((0, 0, {
                    'student_id': student.id,
                    'status': 'present',
                }))
            self.line_ids = lines

    def action_confirm(self):
        Attendance = self.env['school.attendance']
        teacher = self.env['school.teacher'].search(
            [('user_id', '=', self.env.uid)], limit=1
        )
        for line in self.line_ids:
            existing = Attendance.search([
                ('student_id', '=', line.student_id.id),
                ('date', '=', self.date),
            ])
            if existing:
                existing.write({'status': line.status, 'notes': line.notes})
            else:
                Attendance.create({
                    'student_id': line.student_id.id,
                    'class_id': self.class_id.id,
                    'date': self.date,
                    'status': line.status,
                    'notes': line.notes,
                    'teacher_id': teacher.id if teacher else False,
                })
        return {'type': 'ir.actions.act_window_close'}


class AttendanceBulkLine(models.TransientModel):
    _name = 'school.attendance.bulk.line'
    _description = 'Bulk Attendance Line'

    wizard_id = fields.Many2one('school.attendance.bulk', string='Wizard')
    student_id = fields.Many2one('school.student', string='Student', required=True)
    status = fields.Selection([
        ('present', 'Present'),
        ('absent', 'Absent'),
        ('late', 'Late'),
        ('excused', 'Excused'),
    ], string='Status', required=True, default='present')
    notes = fields.Char(string='Notes')
