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

    # Year filter — all year-scoped KPIs follow it (defaults to active year)
    academic_year_id = fields.Many2one(
        'school.academic.year', string='العام الدراسي',
        default=lambda self: self.env['school.academic.year'].get_active_year(),
        help='Switch the dashboard to any year, including archived ones.'
    )
    year_state = fields.Selection(related='academic_year_id.state')

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

    @api.depends('school_id', 'academic_year_id')
    def _compute_fee_kpis(self):
        for rec in self:
            base = rec._school_domain() + rec._year_domain() + \
                [('state', '!=', 'cancelled')]
            fees = self.env['school.fee'].search(base)
            # Net of discounts/credits — matches what is actually payable.
            rec.total_fees_due = sum(fees.mapped('net_payable'))
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

    # ── WP6: year-scoped enrollment / registration / discounts / actions ──
    students_approved = fields.Integer(
        compute='_compute_enrollment_kpis', string='المعتمدون')
    students_target = fields.Integer(
        compute='_compute_enrollment_kpis', string='المستهدف')
    students_kg = fields.Integer(compute='_compute_enrollment_kpis')
    students_primary = fields.Integer(compute='_compute_enrollment_kpis')
    students_middle = fields.Integer(compute='_compute_enrollment_kpis')
    students_secondary = fields.Integer(compute='_compute_enrollment_kpis')

    reg_new = fields.Integer(compute='_compute_registration_kpis')
    reg_pending_docs = fields.Integer(compute='_compute_registration_kpis')
    reg_pending_approval = fields.Integer(compute='_compute_registration_kpis')
    reg_approved = fields.Integer(compute='_compute_registration_kpis')
    reg_rejected = fields.Integer(compute='_compute_registration_kpis')

    disc_total = fields.Monetary(
        compute='_compute_discount_kpis', currency_field='currency_id')
    disc_sibling = fields.Monetary(
        compute='_compute_discount_kpis', currency_field='currency_id')
    disc_manual = fields.Monetary(
        compute='_compute_discount_kpis', currency_field='currency_id')
    disc_reg_credit = fields.Monetary(
        compute='_compute_discount_kpis', currency_field='currency_id')

    act_pending_approvals = fields.Integer(compute='_compute_action_kpis')
    act_pending_overrides = fields.Integer(compute='_compute_action_kpis')
    act_overdue_fees = fields.Integer(compute='_compute_action_kpis')
    act_missing_docs = fields.Integer(compute='_compute_action_kpis')
    act_draft_payments = fields.Integer(compute='_compute_action_kpis')

    def _year_domain(self, field='academic_year_id'):
        return [(field, '=', self.academic_year_id.id)] \
            if self.academic_year_id else []

    @api.depends('school_id', 'academic_year_id')
    def _compute_enrollment_kpis(self):
        for rec in self:
            Enr = self.env['school.student.enrollment']
            base = rec._year_domain()
            enrolled = Enr.search(base + [('state', '=', 'enrolled')])
            rec.students_approved = len(enrolled)
            rec.students_target = self.env.company.target_student_count
            by_stage = {'kg': 0, 'primary': 0, 'middle': 0, 'secondary': 0}
            for e in enrolled:
                stage = e.class_id.stage
                if stage in by_stage:
                    by_stage[stage] += 1
            rec.students_kg = by_stage['kg']
            rec.students_primary = by_stage['primary']
            rec.students_middle = by_stage['middle']
            rec.students_secondary = by_stage['secondary']

    @api.depends('school_id')
    def _compute_registration_kpis(self):
        for rec in self:
            Student = self.env['school.student']
            base = rec._school_domain()
            rec.reg_new = Student.search_count(
                base + [('enrollment_state', '=', 'new')])
            rec.reg_pending_docs = Student.search_count(
                base + [('enrollment_state', '=', 'pending_docs')])
            rec.reg_pending_approval = Student.search_count(
                base + [('enrollment_state', '=', 'pending_approval')])
            rec.reg_approved = Student.search_count(
                base + [('enrollment_state', '=', 'active')])
            rec.reg_rejected = Student.search_count(
                base + [('enrollment_state', '=', 'rejected')])

    @api.depends('school_id', 'academic_year_id')
    def _compute_discount_kpis(self):
        for rec in self:
            fees = self.env['school.fee'].search(
                rec._school_domain() + rec._year_domain()
                + [('state', '!=', 'cancelled')])
            rec.disc_sibling = sum(fees.mapped('sibling_discount_amount'))
            rec.disc_manual = sum(fees.mapped('discount_amount'))
            rec.disc_reg_credit = sum(fees.mapped('registration_credit'))
            rec.disc_total = (rec.disc_sibling + rec.disc_manual
                              + rec.disc_reg_credit)

    @api.depends('school_id', 'academic_year_id')
    def _compute_action_kpis(self):
        for rec in self:
            Student = self.env['school.student']
            Fee = self.env['school.fee']
            sbase = rec._school_domain()
            fbase = rec._school_domain() + rec._year_domain()
            rec.act_pending_approvals = Student.search_count(
                sbase + [('enrollment_state', '=', 'pending_approval')])
            rec.act_pending_overrides = Fee.search_count(
                fbase + [('discount_override_state', '=', 'pending')])
            rec.act_overdue_fees = Fee.search_count(
                fbase + [('state', '=', 'overdue')])
            rec.act_missing_docs = Student.search_count(
                sbase + [('enrollment_state', '=', 'pending_docs')])
            rec.act_draft_payments = self.env['school.fee.payment'].\
                search_count([('state', '=', 'draft')]
                             + ([('fee_id.academic_year_id', '=',
                                  rec.academic_year_id.id)]
                                if rec.academic_year_id else []))

    # ── Click-through actions (each number opens the filtered list) ──
    def _open(self, name, model, domain, context=None):
        return {
            'type': 'ir.actions.act_window',
            'name': name,
            'res_model': model,
            'view_mode': 'tree,form',
            'domain': domain,
            'context': context or {},
        }

    def action_open_pending_approvals(self):
        return self._open('طلبات تنتظر الاعتماد', 'school.student',
                          [('enrollment_state', '=', 'pending_approval')])

    def action_open_missing_docs(self):
        return self._open('بانتظار المستندات', 'school.student',
                          [('enrollment_state', '=', 'pending_docs')])

    def action_open_rejected(self):
        return self._open('طلبات مرفوضة', 'school.student',
                          [('enrollment_state', '=', 'rejected')])

    def action_open_pending_overrides(self):
        return self._open('استثناءات خصم معلقة', 'school.fee',
                          [('discount_override_state', '=', 'pending')])

    def action_open_overdue_fees(self):
        return self._open('رسوم متأخرة', 'school.fee',
                          self._year_domain() + [('state', '=', 'overdue')])

    def action_open_draft_payments(self):
        return self._open('دفعات غير مؤكدة', 'school.fee.payment',
                          [('state', '=', 'draft')])

    def action_open_enrollments(self):
        return self._open('سجلات الالتحاق', 'school.student.enrollment',
                          self._year_domain() + [('state', '=', 'enrolled')])

    def action_open_budget(self):
        action = self.env.ref('school_management.action_budget_report')\
            .read()[0]
        action['domain'] = self._year_domain()
        return action

    @api.model
    def get_or_create(self):
        rec = self.search([], limit=1)
        if not rec:
            rec = self.create({'name': 'School Dashboard'})
        return rec.id
