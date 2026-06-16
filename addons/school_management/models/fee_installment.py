# -*- coding: utf-8 -*-
from odoo import models, fields, api, _
from odoo.exceptions import UserError


class FeeInstallment(models.Model):
    _name = 'school.fee.installment'
    _description = 'Fee Installment'
    _order = 'sequence, due_date'

    fee_id = fields.Many2one(
        'school.fee', string='Fee', required=True, ondelete='cascade'
    )
    currency_id = fields.Many2one(
        'res.currency', related='fee_id.currency_id', store=True
    )
    sequence = fields.Integer(string='#', default=1)
    name = fields.Char(string='Installment', required=True)
    amount = fields.Monetary(
        string='Amount', currency_field='currency_id', required=True
    )
    due_date = fields.Date(string='Due Date', required=True)
    paid_amount = fields.Monetary(
        string='Paid', compute='_compute_paid_amount',
        store=True, currency_field='currency_id'
    )
    balance = fields.Monetary(
        string='Balance', compute='_compute_paid_amount',
        store=True, currency_field='currency_id'
    )
    state = fields.Selection([
        ('pending', 'قيد الانتظار'),
        ('partial', 'مدفوعة جزئيًا'),
        ('paid', 'مدفوعة'),
        ('overdue', 'متأخرة'),
    ], string='Status', default='pending', compute='_compute_state', store=True)
    payment_ids = fields.One2many(
        'school.fee.payment', 'installment_id', string='Payments'
    )

    @api.depends('payment_ids.amount', 'payment_ids.state')
    def _compute_paid_amount(self):
        for rec in self:
            rec.paid_amount = sum(
                p.amount for p in rec.payment_ids if p.state == 'confirmed'
            )
            rec.balance = rec.amount - rec.paid_amount

    @api.depends('balance', 'paid_amount', 'amount', 'due_date')
    def _compute_state(self):
        today = fields.Date.today()
        for rec in self:
            if not rec.amount:
                rec.state = 'pending'
            elif rec.balance <= 0:
                rec.state = 'paid'
            elif rec.paid_amount > 0:
                rec.state = 'partial'
            elif rec.due_date and rec.due_date < today:
                rec.state = 'overdue'
            else:
                rec.state = 'pending'


class FeeScheduleWizard(models.TransientModel):
    _name = 'school.fee.schedule.wizard'
    _description = 'Payment Schedule Wizard'

    fee_id = fields.Many2one('school.fee', string='Fee', required=True)
    total_amount = fields.Monetary(
        string='Total Amount', related='fee_id.amount',
        currency_field='currency_id', readonly=True
    )
    currency_id = fields.Many2one('res.currency', related='fee_id.currency_id')
    installment_count = fields.Selection([
        ('2', 'دفعتان'),
        ('3', 'ثلاث دفعات'),
        ('4', 'أربع دفعات'),
    ], string='عدد الدفعات', default='3', required=True)
    first_due_date = fields.Date(string='تاريخ الدفعة الأولى', required=True)
    interval = fields.Selection([
        ('monthly', 'شهري'),
        ('quarterly', 'ربع سنوي'),
    ], string='الفترة بين الدفعات', default='monthly', required=True)
    line_ids = fields.One2many(
        'school.fee.schedule.wizard.line', 'wizard_id', string='الدفعات'
    )

    def action_generate(self):
        """Auto-generate installment lines from count + interval."""
        from dateutil.relativedelta import relativedelta

        self.line_ids.unlink()
        count = int(self.installment_count)
        fee_amount = self.fee_id.amount
        base_amount = round(fee_amount / count, 2)
        # Last installment absorbs rounding remainder
        remainder = round(fee_amount - base_amount * (count - 1), 2)

        ordinals = ['الأولى', 'الثانية', 'الثالثة', 'الرابعة']
        current_date = self.first_due_date
        lines = []
        for i in range(count):
            amount = remainder if i == count - 1 else base_amount
            lines.append({
                'wizard_id': self.id,
                'sequence': i + 1,
                'name': 'الدفعة %s' % (ordinals[i] if i < len(ordinals) else str(i + 1)),
                'amount': amount,
                'due_date': current_date,
            })
            if self.interval == 'monthly':
                current_date = current_date + relativedelta(months=1)
            else:  # quarterly
                current_date = current_date + relativedelta(months=3)

        self.env['school.fee.schedule.wizard.line'].create(lines)
        # Reload same dialog to display generated lines
        return {
            'type': 'ir.actions.act_window',
            'res_model': 'school.fee.schedule.wizard',
            'res_id': self.id,
            'view_mode': 'form',
            'target': 'new',
            'context': self.env.context,
        }

    def action_apply(self):
        """Save schedule to fee as installments."""
        if not self.line_ids:
            raise UserError(_('الرجاء إنشاء جدول الدفعات أولًا بالضغط على "إنشاء تلقائي".'))

        total = sum(self.line_ids.mapped('amount'))
        if abs(total - self.fee_id.amount) > 0.01:
            raise UserError(
                _('مجموع الدفعات (%.2f) يجب أن يساوي إجمالي الرسوم (%.2f).') % (
                    total, self.fee_id.amount
                )
            )

        fee = self.fee_id
        fee.installment_ids.unlink()

        for line in self.line_ids.sorted('sequence'):
            self.env['school.fee.installment'].create({
                'fee_id': fee.id,
                'sequence': line.sequence,
                'name': line.name,
                'amount': line.amount,
                'due_date': line.due_date,
            })

        fee.payment_mode = 'installments'
        return {'type': 'ir.actions.act_window_close'}


class FeeScheduleWizardLine(models.TransientModel):
    _name = 'school.fee.schedule.wizard.line'
    _description = 'Fee Schedule Wizard Line'
    _order = 'sequence'

    wizard_id = fields.Many2one(
        'school.fee.schedule.wizard', required=True, ondelete='cascade'
    )
    currency_id = fields.Many2one(
        'res.currency', related='wizard_id.currency_id', store=True
    )
    sequence = fields.Integer(string='#', default=1)
    name = fields.Char(string='الدفعة', required=True)
    amount = fields.Monetary(
        string='المبلغ', currency_field='currency_id', required=True
    )
    due_date = fields.Date(string='تاريخ الاستحقاق', required=True)
