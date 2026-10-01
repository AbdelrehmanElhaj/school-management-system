# -*- coding: utf-8 -*-
from odoo import models, fields, api, _
from odoo.exceptions import ValidationError, UserError
from datetime import date


class Student(models.Model):
    _name = 'school.student'
    _description = 'Student'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'name'
    _rec_name = 'name'

    # Personal Information
    name = fields.Char(string='Full Name', required=True, tracking=True)
    student_code = fields.Char(
        string='Student ID', required=True, copy=False,
        default=lambda self: _('New'), tracking=True
    )
    birth_date = fields.Date(string='Date of Birth')
    age = fields.Integer(string='Age', compute='_compute_age', store=False)
    gender = fields.Selection([
        ('male', 'Male'),
        ('female', 'Female'),
    ], string='Gender', required=True, default='male')
    nationality = fields.Many2one('res.country', string='Nationality')
    national_id = fields.Char(string='National ID')
    photo = fields.Binary(string='Photo', attachment=True)
    notes = fields.Text(string='Notes')

    # Academic Information
    class_id = fields.Many2one('school.class', string='Class', tracking=True)
    academic_year_id = fields.Many2one(
        'school.academic.year', string='Academic Year',
        related='class_id.academic_year_id', store=True
    )
    grade_level = fields.Selection(
        related='class_id.grade_level', store=True, string='Grade Level'
    )
    stage = fields.Selection(
        related='class_id.stage', store=True, string='المرحلة'
    )
    school_id = fields.Many2one(
        'school.branch', string='School',
        related='class_id.school_id', store=True
    )
    enrollment_date = fields.Date(string='Enrollment Date', default=fields.Date.today)
    status = fields.Selection([
        ('active', 'Active'),
        ('paused', 'Paused'),
        ('withdrawn', 'Withdrawn'),
        ('transferred', 'Transferred'),
        ('graduated', 'Graduated'),
    ], string='Status', default='active', tracking=True)

    # Enrollment workflow state (separate from operational status)
    enrollment_state = fields.Selection([
        ('new', 'طلب جديد'),
        ('pending_docs', 'بانتظار المستندات'),
        ('pending_approval', 'بانتظار الموافقة'),
        ('active', 'مقبول'),
        ('rejected', 'مرفوض'),
    ], string='Enrollment State', default='new', tracking=True,
       help='Tracks the enrollment process from application to acceptance.')
    rejection_reason = fields.Char(string='سبب الرفض', tracking=True, copy=False)

    # Guardian Information
    guardian_id = fields.Many2one('school.guardian', string='Guardian/Parent')
    guardian_name = fields.Char(
        string='Guardian Name', related='guardian_id.name', readonly=True
    )
    guardian_phone = fields.Char(
        string='Guardian Phone', related='guardian_id.phone', readonly=True
    )

    # Contact
    email = fields.Char(string='Email')
    phone = fields.Char(string='Phone')
    address = fields.Text(string='Address')

    # Yearly enrollment history (one record per academic year)
    enrollment_history_ids = fields.One2many(
        'school.student.enrollment', 'student_id', string='Enrollment History'
    )

    # Enrollment checklist
    checklist_ids = fields.One2many(
        'school.enrollment.checklist.item', 'student_id', string='Enrollment Checklist'
    )
    checklist_pending_count = fields.Integer(
        string='Pending Documents', compute='_compute_checklist_counts'
    )
    checklist_done_count = fields.Integer(
        string='Submitted Documents', compute='_compute_checklist_counts'
    )

    _sql_constraints = [
        ('student_code_unique', 'UNIQUE(student_code)', 'Student ID must be unique.'),
    ]

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get('student_code', _('New')) == _('New'):
                vals['student_code'] = self.env['ir.sequence'].next_by_code(
                    'school.student') or _('New')
        records = super().create(vals_list)
        # Auto-create enrollment checklist items from active requirements
        requirements = self.env['school.enrollment.requirement'].search(
            [('active', '=', True)]
        )
        if requirements:
            checklist_items = []
            for rec in records:
                for req in requirements:
                    checklist_items.append({
                        'student_id': rec.id,
                        'requirement_id': req.id,
                    })
            self.env['school.enrollment.checklist.item'].create(checklist_items)
        return records

    @api.depends('birth_date')
    def _compute_age(self):
        today = date.today()
        for rec in self:
            if rec.birth_date:
                rec.age = today.year - rec.birth_date.year - (
                    (today.month, today.day) < (rec.birth_date.month, rec.birth_date.day)
                )
            else:
                rec.age = 0

    @api.depends('checklist_ids.status', 'checklist_ids.is_required')
    def _compute_checklist_counts(self):
        for rec in self:
            pending = rec.checklist_ids.filtered(
                lambda c: c.is_required and c.status == 'pending'
            )
            done = rec.checklist_ids.filtered(
                lambda c: c.status in ('submitted', 'verified')
            )
            rec.checklist_pending_count = len(pending)
            rec.checklist_done_count = len(done)

    @api.constrains('birth_date')
    def _check_birth_date(self):
        for rec in self:
            if rec.birth_date and rec.birth_date > date.today():
                raise ValidationError(_('Birth date cannot be in the future.'))

    # ── Enrollment workflow actions ────────────────────────────────────────────

    def action_submit_application(self):
        """new → pending_docs"""
        for rec in self:
            if rec.enrollment_state == 'new':
                rec.enrollment_state = 'pending_docs'

    def action_submit_documents(self):
        """pending_docs → pending_approval  (only if all required docs submitted)"""
        for rec in self:
            if rec.enrollment_state != 'pending_docs':
                continue
            pending_required = rec.checklist_ids.filtered(
                lambda c: c.is_required and c.status == 'pending'
            )
            if pending_required:
                names = ', '.join(pending_required.mapped('requirement_name'))
                raise UserError(
                    _('المستندات الإلزامية التالية لم تُرفع بعد: %s') % names
                )
            rec.enrollment_state = 'pending_approval'

    def _check_approver_rights(self):
        """Server-side guard: view-level groups= can be bypassed over RPC."""
        if not self.env.user.has_group(
                'school_management.group_school_approver'):
            raise UserError(_(
                'اعتماد أو رفض التسجيل متاح فقط لمجموعة «معتمِد الطلاب».'))

    def action_approve_enrollment(self):
        """pending_approval → active"""
        self._check_approver_rights()
        for rec in self:
            if (rec.enrollment_state == 'pending_approval'
                    and rec.company_docs_required()):
                pending_required = rec.checklist_ids.filtered(
                    lambda c: c.is_required and c.status == 'pending')
                if pending_required:
                    raise UserError(_(
                        'لا يمكن الاعتماد: مستندات إلزامية ما زالت معلقة (%s). '
                        'يمكن تعطيل هذا الشرط من إعدادات المدرسة.'
                    ) % ', '.join(pending_required.mapped('requirement_name')))
        for rec in self:
            if rec.enrollment_state == 'pending_approval':
                rec.enrollment_state = 'active'
                rec.status = 'active'
                rec._create_enrollment_record()
                rec._generate_fees_from_structure()
                if rec.guardian_id:
                    rec.guardian_id._recompute_sibling_discounts()

    def _generate_fees_from_structure(self):
        """Create this student's fees from the fee matrix of his class's
        year/grade (skipping types/terms that already exist), then apply
        the registration-fee credit on tuition. The heart of the
        'no re-entry' requirement."""
        self.ensure_one()
        if not self.class_id:
            return
        year = self.class_id.academic_year_id
        grade = self.class_id.grade_level
        structures = self.env['school.fee.structure'].search([
            ('academic_year_id', '=', year.id),
            ('grade_level', '=', grade),
        ])
        if not structures:
            return
        Fee = self.env['school.fee']
        existing = Fee.search([
            ('student_id', '=', self.id),
            ('academic_year_id', '=', year.id),
            ('state', '!=', 'cancelled'),
        ])
        existing_keys = {(f.fee_type_id.id, f.term) for f in existing}
        created = Fee.browse()
        for st in structures:
            if (st.fee_type_id.id, st.term) in existing_keys:
                continue
            created |= Fee.create({
                'student_id': self.id,
                'fee_type_id': st.fee_type_id.id,
                'term': st.term,
                'amount': st.amount,
                'currency_id': st.currency_id.id,
                'academic_year_id': year.id,
                'class_id': self.class_id.id,
                'due_date': fields.Date.add(fields.Date.today(), days=30),
                'state': 'due',
            })
        if created:
            self.message_post(body=_(
                'وُلِّدت الرسوم تلقائيًا من مصفوفة رسوم %(year)s: %(fees)s.',
                year=year.name,
                fees=', '.join('%s (%.0f)' % (f.fee_type_id.name, f.amount)
                               for f in created)))
        self._apply_registration_credit(year)
        return created

    def _apply_registration_credit(self, year):
        """Deduct the paid registration fee from the tuition fee of the
        same year (policy-controlled from the billing settings)."""
        self.ensure_one()
        if not self.env.company.registration_fee_deduction:
            return
        tuition = self.env.ref('school_management.fee_type_tuition',
                               raise_if_not_found=False)
        registration = self.env.ref('school_management.fee_type_registration',
                                    raise_if_not_found=False)
        if not tuition or not registration:
            return
        Fee = self.env['school.fee']
        reg_fees = Fee.search([
            ('student_id', '=', self.id),
            ('academic_year_id', '=', year.id),
            ('fee_type_id', '=', registration.id),
            ('state', '!=', 'cancelled'),
        ])
        reg_paid = sum(reg_fees.mapped('paid_amount'))
        if not reg_paid:
            return
        tuition_fee = Fee.search([
            ('student_id', '=', self.id),
            ('academic_year_id', '=', year.id),
            ('fee_type_id', '=', tuition.id),
            ('state', '!=', 'cancelled'),
        ], limit=1)
        if tuition_fee and tuition_fee.registration_credit != reg_paid:
            tuition_fee.registration_credit = reg_paid
            tuition_fee._update_state()
            tuition_fee.message_post(body=_(
                'خُصمت رسوم التسجيل المدفوعة (%(amt).2f) من رسم الدراسة '
                'وفق سياسة الفوترة.', amt=reg_paid))

    def _create_enrollment_record(self):
        """Create the yearly enrollment record for the student's current
        class/year (skipped if one already exists for that year)."""
        self.ensure_one()
        year = self.class_id.academic_year_id or \
            self.env['school.academic.year'].get_active_year()
        if not year:
            return self.env['school.student.enrollment']
        existing = self.env['school.student.enrollment'].search([
            ('student_id', '=', self.id),
            ('academic_year_id', '=', year.id),
        ], limit=1)
        if existing:
            return existing
        enrollment = self.env['school.student.enrollment'].create({
            'student_id': self.id,
            'academic_year_id': year.id,
            'class_id': self.class_id.id,
        })
        self.message_post(body=_(
            'أُنشئ سجل الالتحاق للعام الدراسي %s.') % year.name)
        return enrollment

    def get_qr_code_b64(self):
        """QR of the student code, embedded as base64 so the ID card
        renders without a round-trip to the barcode controller."""
        self.ensure_one()
        import base64
        png = self.env['ir.actions.report'].barcode(
            'QR', self.student_code or str(self.id), width=180, height=180)
        return base64.b64encode(png).decode()

    def company_docs_required(self):
        self.ensure_one()
        return self.env.company.enrollment_require_docs

    def action_reject_enrollment(self):
        """Open the rejection wizard (reason required; record kept for
        statistics instead of being reset)."""
        self._check_approver_rights()
        return {
            'type': 'ir.actions.act_window',
            'name': _('رفض طلب التسجيل'),
            'res_model': 'school.student.reject.wizard',
            'view_mode': 'form',
            'target': 'new',
            'context': {'default_student_ids': [(6, 0, self.ids)]},
        }

    def action_reset_application(self):
        """rejected → new (re-open a rejected application)."""
        self._check_approver_rights()
        for rec in self:
            if rec.enrollment_state == 'rejected':
                rec.write({'enrollment_state': 'new',
                           'rejection_reason': False})

    # ── Operational status actions ─────────────────────────────────────────────

    def action_withdraw(self):
        self.write({'status': 'withdrawn'})
        # Reflect the withdrawal on the active-year enrollment record.
        active_year = self.env['school.academic.year'].get_active_year()
        if active_year:
            self.env['school.student.enrollment'].search([
                ('student_id', 'in', self.ids),
                ('academic_year_id', '=', active_year.id),
                ('state', '=', 'enrolled'),
            ]).write({'state': 'withdrawn'})
        # Siblings' discount drops with the approved-children count.
        self.mapped('guardian_id')._recompute_sibling_discounts()

    def action_activate(self):
        self.write({'status': 'active'})

    def action_transfer(self):
        self.write({'status': 'transferred'})

    def action_pause(self):
        self.write({'status': 'paused'})


class Guardian(models.Model):
    _name = 'school.guardian'
    _description = 'Guardian / Parent'
    _inherit = ['mail.thread']
    _rec_name = 'name'

    name = fields.Char(string='Full Name', required=True)
    national_id = fields.Char(string='National ID')
    phone = fields.Char(string='Phone', required=True)
    mobile = fields.Char(string='Mobile')
    email = fields.Char(string='Email')
    address = fields.Text(string='Address')
    relationship = fields.Selection([
        ('father', 'Father'),
        ('mother', 'Mother'),
        ('guardian', 'Guardian'),
        ('other', 'Other'),
    ], string='Relationship', default='father')
    student_ids = fields.One2many('school.student', 'guardian_id', string='Children List')
    student_count = fields.Integer(string='Children', compute='_compute_student_count')
    approved_children_count = fields.Integer(
        string='الأبناء المعتمدون (العام النشط)',
        compute='_compute_approved_children_count',
        help='Children with an enrollment record in the active academic '
             'year — drives the sibling discount.'
    )
    sibling_discount_percent = fields.Float(
        string='نسبة خصم الأشقاء', compute='_compute_approved_children_count'
    )
    user_id = fields.Many2one('res.users', string='Portal User')
    notes = fields.Text(string='Notes')

    @api.depends('student_ids')
    def _compute_student_count(self):
        for rec in self:
            rec.student_count = len(rec.student_ids)

    def _get_approved_children(self, year=None):
        """Children with an active (enrolled) enrollment record in the
        given/active year."""
        year = year or self.env['school.academic.year'].get_active_year()
        if not year:
            return self.env['school.student']
        enrollments = self.env['school.student.enrollment'].search([
            ('student_id.guardian_id', 'in', self.ids),
            ('academic_year_id', '=', year.id),
            ('state', '=', 'enrolled'),
            ('student_id.enrollment_state', '=', 'active'),
        ])
        return enrollments.mapped('student_id')

    def _compute_approved_children_count(self):
        Rule = self.env['school.sibling.discount.rule']
        for rec in self:
            count = len(rec._get_approved_children())
            rec.approved_children_count = count
            rec.sibling_discount_percent = Rule.get_percent_for_count(count)

    def _get_sibling_percent(self, year=None):
        self.ensure_one()
        count = len(self._get_approved_children(year))
        return self.env['school.sibling.discount.rule'].get_percent_for_count(
            count)

    def _recompute_sibling_discounts(self, year=None):
        """(Re)apply the sibling percent on all children's not-fully-paid
        tuition fees of the active year. Fully paid fees are left alone;
        a changed percent on partially paid fees is flagged to finance."""
        year = year or self.env['school.academic.year'].get_active_year()
        if not year:
            return
        tuition = self.env.ref('school_management.fee_type_tuition',
                               raise_if_not_found=False)
        if not tuition:
            return
        for guardian in self:
            percent = guardian._get_sibling_percent(year)
            fees = self.env['school.fee'].search([
                ('guardian_id', '=', guardian.id),
                ('academic_year_id', '=', year.id),
                ('fee_type_id', '=', tuition.id),
                ('state', 'not in', ['cancelled', 'paid']),
            ])
            for fee in fees:
                if fee.sibling_discount_percent == percent:
                    continue
                old = fee.sibling_discount_percent
                fee.sibling_discount_percent = percent
                fee._update_state()
                note = _(
                    'تحدّثت نسبة خصم الأشقاء من %(old).0f%% إلى %(new).0f%% '
                    '(عدد الأبناء المعتمدين: %(cnt)d).',
                    old=old, new=percent,
                    cnt=guardian.approved_children_count)
                if fee.paid_amount:
                    note += _(' تنبيه للمالية: الرسم عليه مدفوعات جزئية — '
                              'النسبة الجديدة تسري على الرصيد غير المسدد.')
                fee.message_post(body=note)

    def action_view_students(self):
        return {
            'type': 'ir.actions.act_window',
            'name': _('Children'),
            'res_model': 'school.student',
            'view_mode': 'tree,form',
            'domain': [('guardian_id', '=', self.id)],
            'context': {'default_guardian_id': self.id},
        }
