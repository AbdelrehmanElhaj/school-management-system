# -*- coding: utf-8 -*-
from odoo import models, fields, api, _
from odoo.exceptions import ValidationError, UserError


class FeeType(models.Model):
    _name = 'school.fee.type'
    _description = 'Fee Type'
    _order = 'name'

    name = fields.Char(string='Fee Type', required=True, translate=True)
    code = fields.Char(string='Code', required=True)
    description = fields.Text(string='Description')
    default_amount = fields.Monetary(
        string='Default Amount', currency_field='currency_id'
    )
    currency_id = fields.Many2one(
        'res.currency', string='Currency',
        default=lambda self: self.env.company.currency_id
    )
    active = fields.Boolean(string='Active', default=True)

    _sql_constraints = [
        ('code_unique', 'UNIQUE(code)', 'Fee type code must be unique.'),
    ]


class Fee(models.Model):
    _name = 'school.fee'
    _description = 'Student Fee'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'due_date, student_id'
    _rec_name = 'display_name'

    display_name = fields.Char(
        string='Reference', compute='_compute_display_name', store=True
    )
    fee_code = fields.Char(
        string='Fee ID', required=True, copy=False,
        default=lambda self: _('New'), readonly=True
    )
    student_id = fields.Many2one(
        'school.student', string='Student', required=True, tracking=True
    )
    guardian_id = fields.Many2one(
        'school.guardian', string='Guardian',
        related='student_id.guardian_id', store=True
    )
    # Snapshot fields: filled from the student at creation time and then
    # frozen, so promoting the student to a new year/class never rewrites
    # historical financial records (previously related store=True).
    class_id = fields.Many2one(
        'school.class', string='Class', index=True
    )
    stage = fields.Selection(
        related='class_id.stage', store=True, string='المرحلة'
    )
    school_id = fields.Many2one(
        'school.branch', string='School',
        related='student_id.school_id', store=True
    )
    academic_year_id = fields.Many2one(
        'school.academic.year', string='Academic Year',
        required=True, index=True,
        default=lambda self: self.env['school.academic.year'].get_active_year()
    )
    fee_type_id = fields.Many2one(
        'school.fee.type', string='Fee Type', required=True, tracking=True
    )
    term = fields.Selection([
        ('first', 'First Term'),
        ('second', 'Second Term'),
        ('third', 'Third Term'),
        ('annual', 'Annual'),
    ], string='Term', required=True, default='annual', tracking=True)
    currency_id = fields.Many2one(
        'res.currency', string='Currency',
        default=lambda self: self.env.company.currency_id
    )
    amount = fields.Monetary(
        string='Amount Due', required=True, currency_field='currency_id', tracking=True
    )
    paid_amount = fields.Monetary(
        string='Amount Paid', compute='_compute_paid_amount',
        store=True, currency_field='currency_id'
    )
    balance = fields.Monetary(
        string='Balance', compute='_compute_balance',
        store=True, currency_field='currency_id'
    )
    due_date = fields.Date(string='Due Date', required=True, tracking=True)
    state = fields.Selection([
        ('draft', 'Draft'),
        ('due', 'Due'),
        ('partial', 'Partially Paid'),
        ('paid', 'Paid'),
        ('overdue', 'Overdue'),
        ('cancelled', 'Cancelled'),
    ], string='Status', default='draft', tracking=True)

    # Payment mode and installments
    payment_mode = fields.Selection([
        ('single', 'دفعة واحدة'),
        ('installments', 'أقساط'),
    ], string='Payment Mode', default='single', tracking=True)
    installment_ids = fields.One2many(
        'school.fee.installment', 'fee_id', string='Installments'
    )
    installment_count = fields.Integer(
        string='Installments', compute='_compute_installment_count'
    )

    payment_ids = fields.One2many(
        'school.fee.payment', 'fee_id', string='Payments'
    )
    payment_count = fields.Integer(
        string='Payments', compute='_compute_payment_count'
    )
    notes = fields.Text(string='Notes')
    invoice_date = fields.Date(string='Invoice Date', default=fields.Date.today)

    discount_amount = fields.Monetary(
        string='Discount', currency_field='currency_id', tracking=True
    )
    discount_reason = fields.Char(string='Discount Reason')
    is_exempt = fields.Boolean(
        string='Fee Exempt', tracking=True,
        help='Student is fully exempted from this fee (معفي).'
    )

    # ── WP3: sibling discount, registration credit, override cycle ──
    sibling_discount_percent = fields.Float(
        string='خصم الأشقاء %', readonly=True, tracking=True,
        help='Set automatically from the sibling discount rules; applied '
             'on tuition fees only.'
    )
    sibling_discount_amount = fields.Monetary(
        string='مبلغ خصم الأشقاء', currency_field='currency_id',
        compute='_compute_sibling_discount_amount', store=True
    )
    registration_credit = fields.Monetary(
        string='رصيد رسوم التسجيل', currency_field='currency_id',
        readonly=True, tracking=True,
        help='Paid registration fee deducted from this tuition fee '
             '(per the billing settings).'
    )
    net_payable = fields.Monetary(
        string='الصافي المستحق', currency_field='currency_id',
        compute='_compute_net_payable', store=True
    )
    discount_override_amount = fields.Monetary(
        string='الخصم المقترح', currency_field='currency_id', tracking=True
    )
    discount_override_reason = fields.Char(string='سبب الخصم المقترح')
    discount_override_state = fields.Selection([
        ('none', 'بدون'),
        ('pending', 'بانتظار الاعتماد'),
        ('approved', 'معتمد'),
        ('refused', 'مرفوض'),
    ], string='حالة الاستثناء', default='none', tracking=True)
    discount_override_user_id = fields.Many2one(
        'res.users', string='طلبه', readonly=True, copy=False
    )
    discount_override_approver_id = fields.Many2one(
        'res.users', string='اعتمده', readonly=True, copy=False
    )

    _sql_constraints = [
        ('fee_code_unique', 'UNIQUE(fee_code)', 'Fee ID must be unique.'),
    ]

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get('fee_code', _('New')) == _('New'):
                vals['fee_code'] = self.env['ir.sequence'].next_by_code(
                    'school.fee') or _('New')
            # Snapshot year/class from the student's current situation when
            # not given explicitly (covers RPC/import paths with no onchange).
            if vals.get('student_id'):
                student = self.env['school.student'].browse(vals['student_id'])
                if not vals.get('class_id') and student.class_id:
                    vals['class_id'] = student.class_id.id
                if not vals.get('academic_year_id') and student.academic_year_id:
                    vals['academic_year_id'] = student.academic_year_id.id
        return super().create(vals_list)

    @api.onchange('student_id')
    def _onchange_student_snapshot(self):
        # Proposed from the student's current class/year, then stays frozen.
        self.class_id = self.student_id.class_id
        if self.student_id.academic_year_id:
            self.academic_year_id = self.student_id.academic_year_id

    @api.depends('student_id', 'fee_type_id')
    def _compute_display_name(self):
        for rec in self:
            student = rec.student_id.name or ''
            fee_type = rec.fee_type_id.name or ''
            rec.display_name = f"{student} - {fee_type}" if student else fee_type

    @api.depends('payment_ids.amount', 'payment_ids.state')
    def _compute_paid_amount(self):
        for rec in self:
            rec.paid_amount = sum(
                p.amount for p in rec.payment_ids if p.state == 'confirmed'
            )

    @api.depends('amount', 'sibling_discount_percent')
    def _compute_sibling_discount_amount(self):
        for rec in self:
            rec.sibling_discount_amount = (
                rec.amount * rec.sibling_discount_percent / 100.0)

    @api.depends('amount', 'discount_amount', 'sibling_discount_amount',
                 'registration_credit', 'is_exempt')
    def _compute_net_payable(self):
        for rec in self:
            if rec.is_exempt:
                rec.net_payable = 0.0
            else:
                rec.net_payable = max(0.0, rec.amount - rec.discount_amount
                                      - rec.sibling_discount_amount
                                      - rec.registration_credit)

    @api.depends('net_payable', 'paid_amount', 'is_exempt')
    def _compute_balance(self):
        for rec in self:
            if rec.is_exempt:
                rec.balance = 0.0
            else:
                rec.balance = rec.net_payable - rec.paid_amount

    @api.depends('payment_ids')
    def _compute_payment_count(self):
        for rec in self:
            rec.payment_count = len(rec.payment_ids)

    @api.depends('installment_ids')
    def _compute_installment_count(self):
        for rec in self:
            rec.installment_count = len(rec.installment_ids)

    @api.onchange('fee_type_id')
    def _onchange_fee_type(self):
        if self.fee_type_id and self.fee_type_id.default_amount:
            self.amount = self.fee_type_id.default_amount

    @api.constrains('amount')
    def _check_amount(self):
        for rec in self:
            if rec.amount <= 0:
                raise ValidationError(_('Fee amount must be greater than zero.'))

    def _update_state(self):
        today = fields.Date.today()
        for rec in self:
            if rec.state == 'cancelled':
                continue
            if rec.is_exempt or rec.balance <= 0:
                rec.state = 'paid'
            elif rec.paid_amount > 0:
                rec.state = 'partial'
            elif rec.payment_mode == 'installments' and rec.installment_ids:
                # Check if any unpaid installment is overdue
                overdue = rec.installment_ids.filtered(
                    lambda i: i.due_date and i.due_date < today and i.state != 'paid'
                )
                rec.state = 'overdue' if overdue else 'due'
            elif rec.due_date and rec.due_date < today:
                rec.state = 'overdue'
            else:
                rec.state = 'due'

    def write(self, vals):
        # Manual discount changes on confirmed fees go through the override
        # cycle; only approvers may touch the applied discount directly.
        if ('discount_amount' in vals or 'is_exempt' in vals) and \
                not self.env.su and not self.env.user.has_group(
                    'school_management.group_school_approver'):
            non_draft = self.filtered(lambda f: f.state != 'draft')
            if non_draft:
                raise UserError(_(
                    'تعديل الخصم أو الإعفاء على رسم مؤكد يتطلب طلب استثناء '
                    'يعتمده «معتمِد الطلاب» (زر «طلب استثناء خصم»).'))
        return super().write(vals)

    # ── Discount override cycle: finance proposes, approver decides ──
    def action_request_discount_override(self):
        for rec in self:
            if rec.discount_override_amount <= 0:
                raise UserError(_('أدخل مبلغ الخصم المقترح أولًا.'))
            if not rec.discount_override_reason:
                raise UserError(_('أدخل سبب الخصم المقترح.'))
            rec.write({
                'discount_override_state': 'pending',
                'discount_override_user_id': self.env.user.id,
            })
            rec.message_post(body=_(
                'طلب استثناء خصم: %(amt).2f — %(reason)s',
                amt=rec.discount_override_amount,
                reason=rec.discount_override_reason))

    def _check_override_approver(self):
        if not self.env.user.has_group(
                'school_management.group_school_approver'):
            raise UserError(_(
                'اعتماد استثناءات الخصم متاح فقط لمجموعة «معتمِد الطلاب».'))

    def action_approve_discount_override(self):
        self._check_override_approver()
        for rec in self:
            if rec.discount_override_state != 'pending':
                continue
            rec.write({
                'discount_amount': rec.discount_override_amount,
                'discount_reason': rec.discount_override_reason,
                'discount_override_state': 'approved',
                'discount_override_approver_id': self.env.user.id,
            })
            rec.message_post(body=_(
                'اعتُمد استثناء الخصم (%(amt).2f) بواسطة %(user)s.',
                amt=rec.discount_override_amount,
                user=self.env.user.name))
            rec._update_state()

    def action_refuse_discount_override(self):
        self._check_override_approver()
        for rec in self:
            if rec.discount_override_state == 'pending':
                rec.write({
                    'discount_override_state': 'refused',
                    'discount_override_approver_id': self.env.user.id,
                })
                rec.message_post(body=_('رُفض استثناء الخصم.'))

    def action_confirm(self):
        for rec in self:
            if rec.state == 'draft':
                if (rec.student_id and
                        rec.student_id.enrollment_state != 'active'):
                    raise UserError(
                        _('لا يمكن تأكيد الرسوم: الطالب "%s" لم يُكمل إجراءات التسجيل بعد.')
                        % rec.student_id.name
                    )
                rec.state = 'due'

    def action_cancel(self):
        for rec in self:
            if rec.payment_ids.filtered(lambda p: p.state == 'confirmed'):
                raise UserError(
                    _('Cannot cancel a fee that has confirmed payments.')
                )
            rec.state = 'cancelled'

    def action_draft(self):
        self.write({'state': 'draft'})

    def action_schedule_payments(self):
        """Open payment schedule wizard."""
        return {
            'type': 'ir.actions.act_window',
            'name': _('جدولة الدفعات'),
            'res_model': 'school.fee.schedule.wizard',
            'view_mode': 'form',
            'target': 'new',
            'context': {
                'default_fee_id': self.id,
                'default_first_due_date': self.due_date,
            },
        }

    def action_register_payment(self):
        ctx = {
            'default_fee_id': self.id,
            'default_amount': self.balance,
        }
        # Pre-select first unpaid installment when in installment mode
        if self.payment_mode == 'installments' and self.installment_ids:
            first_unpaid = self.installment_ids.filtered(
                lambda i: i.state not in ('paid',)
            ).sorted('sequence')
            if first_unpaid:
                ctx['default_installment_id'] = first_unpaid[0].id
                ctx['default_amount'] = first_unpaid[0].balance
        return {
            'type': 'ir.actions.act_window',
            'name': _('Register Payment'),
            'res_model': 'school.fee.payment.wizard',
            'view_mode': 'form',
            'target': 'new',
            'context': ctx,
        }

    def action_view_payments(self):
        return {
            'type': 'ir.actions.act_window',
            'name': _('Payments'),
            'res_model': 'school.fee.payment',
            'view_mode': 'tree,form',
            'domain': [('fee_id', '=', self.id)],
            'context': {'default_fee_id': self.id},
        }

    def action_send_reminder(self):
        template = self.env.ref(
            'school_management.email_template_fee_reminder', raise_if_not_found=False
        )
        for rec in self:
            if template and rec.guardian_id and rec.guardian_id.email:
                template.send_mail(rec.id, force_send=True)
        return True

    @api.model
    def cron_mark_overdue_and_remind(self):
        """Called by cron: mark overdue fees and send email reminders."""
        today = fields.Date.today()
        # Single-mode: use due_date on fee
        overdue_single = self.search([
            ('state', 'in', ['due', 'partial']),
            ('payment_mode', '=', 'single'),
            ('due_date', '<', today),
        ])
        overdue_single.write({'state': 'overdue'})
        # Installment-mode: check individual installment due dates
        installment_fees = self.search([
            ('state', 'in', ['due', 'partial']),
            ('payment_mode', '=', 'installments'),
        ])
        for fee in installment_fees:
            if fee.installment_ids.filtered(
                lambda i: i.due_date and i.due_date < today and i.state != 'paid'
            ):
                fee.state = 'overdue'
        overdue_all = overdue_single | installment_fees.filtered(
            lambda f: f.state == 'overdue'
        )
        template = self.env.ref(
            'school_management.email_template_fee_reminder', raise_if_not_found=False
        )
        if template:
            for fee in overdue_all.filtered(lambda f: f.guardian_id.email):
                try:
                    template.send_mail(fee.id, force_send=True)
                except Exception:
                    pass


class FeePayment(models.Model):
    _name = 'school.fee.payment'
    _description = 'Fee Payment'
    _inherit = ['mail.thread']
    _order = 'payment_date desc'
    _rec_name = 'display_name'

    display_name = fields.Char(
        string='Reference', compute='_compute_display_name', store=True
    )
    payment_code = fields.Char(
        string='Receipt No.', required=True, copy=False,
        default=lambda self: _('New'), readonly=True
    )
    fee_id = fields.Many2one(
        'school.fee', string='Fee', required=True, tracking=True
    )
    installment_id = fields.Many2one(
        'school.fee.installment', string='Installment',
        domain="[('fee_id', '=', fee_id), ('state', '!=', 'paid')]"
    )
    student_id = fields.Many2one(
        'school.student', string='Student',
        related='fee_id.student_id', store=True
    )
    guardian_id = fields.Many2one(
        'school.guardian', string='Guardian',
        related='fee_id.guardian_id', store=True
    )
    currency_id = fields.Many2one(
        'res.currency', related='fee_id.currency_id', store=True
    )
    amount = fields.Monetary(
        string='Amount', required=True, currency_field='currency_id', tracking=True
    )
    payment_date = fields.Date(
        string='Payment Date', required=True,
        default=fields.Date.today, tracking=True
    )
    payment_method = fields.Selection([
        ('cash', 'Cash'),
        ('bank_transfer', 'Bank Transfer'),
        ('cheque', 'Cheque'),
        ('online', 'Online'),
    ], string='Payment Method', default='cash', tracking=True)
    state = fields.Selection([
        ('draft', 'Draft'),
        ('confirmed', 'Confirmed'),
        ('cancelled', 'Cancelled'),
    ], string='Status', default='draft', tracking=True)
    received_by = fields.Many2one(
        'res.users', string='Received By', default=lambda self: self.env.user
    )
    notes = fields.Text(string='Notes')

    _sql_constraints = [
        ('payment_code_unique', 'UNIQUE(payment_code)', 'Receipt number must be unique.'),
    ]

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get('payment_code', _('New')) == _('New'):
                vals['payment_code'] = self.env['ir.sequence'].next_by_code(
                    'school.fee.payment') or _('New')
        return super().create(vals_list)

    @api.depends('fee_id', 'payment_date')
    def _compute_display_name(self):
        for rec in self:
            fee = rec.fee_id.display_name or ''
            date_str = str(rec.payment_date) if rec.payment_date else ''
            rec.display_name = f"{fee} / {date_str}" if fee else date_str

    @api.constrains('amount')
    def _check_amount(self):
        for rec in self:
            if rec.amount <= 0:
                raise ValidationError(_('Payment amount must be greater than zero.'))
            if rec.fee_id:
                confirmed_others = sum(
                    p.amount for p in rec.fee_id.payment_ids
                    if p.state == 'confirmed' and p.id != rec.id
                )
                payable = rec.fee_id.net_payable
                if rec.amount + confirmed_others > payable:
                    raise ValidationError(
                        _('Total payments (%.2f) would exceed the payable amount '
                          'after discount (%.2f).') % (
                            rec.amount + confirmed_others, payable
                        )
                    )

    def action_confirm(self):
        for rec in self:
            rec.state = 'confirmed'
            rec.fee_id._update_state()
            template = self.env.ref(
                'school_management.email_template_payment_receipt',
                raise_if_not_found=False
            )
            if template and rec.guardian_id and rec.guardian_id.email:
                template.send_mail(rec.id, force_send=False)

    def action_cancel(self):
        for rec in self:
            rec.state = 'cancelled'
            rec.fee_id._update_state()

    def action_draft(self):
        self.write({'state': 'draft'})


class FeePaymentWizard(models.TransientModel):
    _name = 'school.fee.payment.wizard'
    _description = 'Register Fee Payment Wizard'

    fee_id = fields.Many2one('school.fee', string='Fee', required=True)
    fee_payment_mode = fields.Selection(related='fee_id.payment_mode', readonly=True)
    installment_id = fields.Many2one(
        'school.fee.installment', string='Installment',
        domain="[('fee_id', '=', fee_id), ('state', '!=', 'paid')]"
    )
    installment_balance = fields.Monetary(
        string='Installment Balance', related='installment_id.balance',
        currency_field='currency_id', readonly=True
    )
    student_id = fields.Many2one(
        'school.student', related='fee_id.student_id', readonly=True
    )
    fee_amount = fields.Monetary(
        string='Fee Amount', related='fee_id.amount',
        currency_field='currency_id', readonly=True
    )
    balance = fields.Monetary(
        string='Outstanding Balance', related='fee_id.balance',
        currency_field='currency_id', readonly=True
    )
    currency_id = fields.Many2one(
        'res.currency', related='fee_id.currency_id'
    )
    amount = fields.Monetary(
        string='Payment Amount', required=True, currency_field='currency_id'
    )
    payment_date = fields.Date(
        string='Payment Date', required=True, default=fields.Date.today
    )
    payment_method = fields.Selection([
        ('cash', 'Cash'),
        ('bank_transfer', 'Bank Transfer'),
        ('cheque', 'Cheque'),
        ('online', 'Online'),
    ], string='Payment Method', default='cash', required=True)
    notes = fields.Text(string='Notes')

    @api.onchange('installment_id')
    def _onchange_installment_id(self):
        if self.installment_id:
            self.amount = self.installment_id.balance

    def action_confirm(self):
        payment = self.env['school.fee.payment'].create({
            'fee_id': self.fee_id.id,
            'installment_id': self.installment_id.id if self.installment_id else False,
            'amount': self.amount,
            'payment_date': self.payment_date,
            'payment_method': self.payment_method,
            'notes': self.notes,
        })
        payment.action_confirm()
        return {'type': 'ir.actions.act_window_close'}
