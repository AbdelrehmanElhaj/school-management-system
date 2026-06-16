# -*- coding: utf-8 -*-
from odoo import models, fields, api, _


class TeacherAttendance(models.Model):
    _name = 'school.teacher.attendance'
    _description = 'Teacher Attendance'
    _order = 'date desc, teacher_id'
    _rec_name = 'display_name'

    display_name = fields.Char(
        string='Reference', compute='_compute_display_name', store=True
    )
    teacher_id = fields.Many2one(
        'school.teacher', string='Teacher', required=True, ondelete='restrict'
    )
    school_id = fields.Many2one(
        'school.branch', string='School',
        related='teacher_id.school_id', store=True
    )
    date = fields.Date(string='Date', required=True, default=fields.Date.today)
    check_in = fields.Datetime(string='Check-In Time')
    check_out = fields.Datetime(string='Check-Out Time')
    duration = fields.Float(
        string='Duration (hours)', compute='_compute_duration', store=True
    )
    status = fields.Selection([
        ('present', 'حاضر'),
        ('late', 'متأخر'),
        ('half_day', 'نصف يوم'),
        ('absent', 'غائب'),
        ('on_leave', 'إجازة'),
    ], string='Status', compute='_compute_status', store=True)
    source = fields.Selection([
        ('qr', 'QR Code'),
        ('manual', 'Manual'),
    ], string='Source', default='qr')
    notes = fields.Text(string='Notes')

    _sql_constraints = [
        ('teacher_date_unique', 'UNIQUE(teacher_id, date)',
         'Attendance record already exists for this teacher on this date.'),
    ]

    @api.depends('teacher_id', 'date')
    def _compute_display_name(self):
        for rec in self:
            teacher = rec.teacher_id.name or ''
            date = str(rec.date) if rec.date else ''
            rec.display_name = f"{teacher} / {date}"

    @api.depends('check_in', 'check_out')
    def _compute_duration(self):
        for rec in self:
            if rec.check_in and rec.check_out:
                delta = rec.check_out - rec.check_in
                rec.duration = delta.total_seconds() / 3600.0
            else:
                rec.duration = 0.0

    @api.depends('check_in', 'check_out', 'duration')
    def _compute_status(self):
        for rec in self:
            if not rec.check_in:
                rec.status = 'absent'
                continue
            # Check if late: check-in after 08:15 local time
            check_in_hour = rec.check_in.hour + rec.check_in.minute / 60.0
            if check_in_hour > 8.25:
                if rec.duration and rec.duration < 4:
                    rec.status = 'half_day'
                else:
                    rec.status = 'late'
            else:
                if rec.check_out and rec.duration < 4:
                    rec.status = 'half_day'
                else:
                    rec.status = 'present'
