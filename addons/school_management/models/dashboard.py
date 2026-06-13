# -*- coding: utf-8 -*-
from odoo import models, fields, api
from datetime import date, timedelta


class SchoolDashboard(models.Model):
    _name = 'school.dashboard'
    _description = 'School Dashboard'

    name = fields.Char(default='School Dashboard')
    currency_id = fields.Many2one(
        'res.currency', default=lambda self: self.env.company.currency_id
    )
    # School filter — when set all KPIs are scoped to this branch
    school_id = fields.Many2one(
        'school.branch', string='School / Campus',
        help='Filter dashboard to a specific school. Leave empty to see all schools.'
    )

    # ── Students ──────────────────────────────────────────────────────────────
    total_students = fields.Integer(compute='_compute_student_kpis', string='Active Students')
    new_students_month = fields.Integer(compute='_compute_student_kpis', string='New This Month')
    male_students = fields.Integer(compute='_compute_student_kpis', string='Male')
    female_students = fields.Integer(compute='_compute_student_kpis', string='Female')

    # ── Staff & Classes ───────────────────────────────────────────────────────
    total_teachers = fields.Integer(compute='_compute_staff_kpis', string='Teachers')
    total_classes = fields.Integer(compute='_compute_staff_kpis', string='Open Classes')

    # ── Attendance ────────────────────────────────────────────────────────────
    today_attendance_rate = fields.Float(compute='_compute_attendance_kpis', string='Today %', digits=(5, 1))
    week_attendance_rate = fields.Float(compute='_compute_attendance_kpis', string='This Week %', digits=(5, 1))
    today_absent = fields.Integer(compute='_compute_attendance_kpis', string='Absent Today')

    # ── Fees ──────────────────────────────────────────────────────────────────
    total_fees_due = fields.Monetary(compute='_compute_fee_kpis', string='Total Billed', currency_field='currency_id')
    total_fees_paid = fields.Monetary(compute='_compute_fee_kpis', string='Collected', currency_field='currency_id')
    total_fees_outstanding = fields.Monetary(compute='_compute_fee_kpis', string='Outstanding', currency_field='currency_id')
    collection_rate = fields.Float(compute='_compute_fee_kpis', string='Collection Rate %', digits=(5, 1))
    overdue_fees_count = fields.Integer(compute='_compute_fee_kpis', string='Overdue Fees')

    # ── Grades ────────────────────────────────────────────────────────────────
    avg_grade = fields.Float(compute='_compute_grade_kpis', string='Avg Grade %', digits=(5, 1))
    pass_rate = fields.Float(compute='_compute_grade_kpis', string='Pass Rate %', digits=(5, 1))
    total_grades = fields.Integer(compute='_compute_grade_kpis', string='Grade Entries')

    def _school_domain(self):
        """Return school filter domain fragment if a school is selected."""
        return [('school_id', '=', self.school_id.id)] if self.school_id else []

    @api.depends('school_id')
    def _compute_student_kpis(self):
        today = date.today()
        for rec in self:
            base = rec._school_domain()
            Student = self.env['school.student']
            rec.total_students = Student.search_count(base + [('status', '=', 'active')])
            rec.new_students_month = Student.search_count(base + [
                ('enrollment_date', '>=', today.replace(day=1)),
                ('status', '=', 'active'),
            ])
            rec.male_students = Student.search_count(base + [('status', '=', 'active'), ('gender', '=', 'male')])
            rec.female_students = Student.search_count(base + [('status', '=', 'active'), ('gender', '=', 'female')])

    @api.depends('school_id')
    def _compute_staff_kpis(self):
        for rec in self:
            base = rec._school_domain()
            rec.total_teachers = self.env['school.teacher'].search_count(base + [('status', '=', 'active')])
            rec.total_classes = self.env['school.class'].search_count(base + [('state', '=', 'open')])

    @api.depends('school_id')
    def _compute_attendance_kpis(self):
        today = date.today()
        week_start = today - timedelta(days=today.weekday())
        for rec in self:
            base = rec._school_domain()
            Att = self.env['school.attendance']
            today_recs = Att.search(base + [('date', '=', today)])
            if today_recs:
                present = len(today_recs.filtered(lambda r: r.status in ('present', 'late')))
                rec.today_attendance_rate = present / len(today_recs) * 100
                rec.today_absent = len(today_recs.filtered(lambda r: r.status == 'absent'))
            else:
                rec.today_attendance_rate = 0.0
                rec.today_absent = 0
            week_recs = Att.search(base + [('date', '>=', week_start), ('date', '<=', today)])
            if week_recs:
                present = len(week_recs.filtered(lambda r: r.status in ('present', 'late')))
                rec.week_attendance_rate = present / len(week_recs) * 100
            else:
                rec.week_attendance_rate = 0.0

    @api.depends('school_id')
    def _compute_fee_kpis(self):
        for rec in self:
            base = rec._school_domain()
            fees = self.env['school.fee'].search(base)
            rec.total_fees_due = sum(fees.mapped('amount'))
            rec.total_fees_paid = sum(fees.mapped('paid_amount'))
            rec.total_fees_outstanding = sum(fees.mapped('balance'))
            rec.collection_rate = (rec.total_fees_paid / rec.total_fees_due * 100) if rec.total_fees_due else 0.0
            rec.overdue_fees_count = self.env['school.fee'].search_count(base + [('state', '=', 'overdue')])
            rec.currency_id = self.env.company.currency_id

    @api.depends('school_id')
    def _compute_grade_kpis(self):
        for rec in self:
            base = rec._school_domain()
            grades = self.env['school.grade'].search(base)
            rec.total_grades = len(grades)
            if grades:
                rec.avg_grade = sum(grades.mapped('percentage')) / len(grades)
                rec.pass_rate = len(grades.filtered('passed')) / len(grades) * 100
            else:
                rec.avg_grade = 0.0
                rec.pass_rate = 0.0

    @api.model
    def get_or_create(self):
        rec = self.search([], limit=1)
        if not rec:
            rec = self.create({'name': 'School Dashboard'})
        return rec.id
