# -*- coding: utf-8 -*-
from odoo import models, fields, api, tools, _
from odoo.exceptions import UserError


class FinanceItem(models.Model):
    """Configurable income/expense budget items (بنود الموازنة).
    Managed by the configuration group only; deactivating hides an item
    from new entries without deleting its history."""
    _name = 'school.finance.item'
    _description = 'Finance Item (Income/Expense)'
    _order = 'kind, sequence, code'

    name = fields.Char(string='البند', required=True, translate=True)
    code = fields.Char(string='الرمز', required=True)
    kind = fields.Selection([
        ('income', 'إيراد'),
        ('expense', 'مصروف'),
    ], string='النوع', required=True, default='expense')
    calc_method = fields.Selection([
        ('fixed', 'مبلغ ثابت'),
        ('per_student', 'لكل طالب'),
        ('manual', 'إدخال يدوي'),
    ], string='طريقة الاحتساب', default='manual')
    fee_type_id = fields.Many2one(
        'school.fee.type', string='نوع الرسم المرتبط',
        help='Income items linked to a fee type aggregate automatically '
             'from confirmed payments — no re-entry.'
    )
    account_id = fields.Many2one(
        'account.account', string='الحساب المحاسبي',
        help='Optional link to the chart of accounts.'
    )
    sequence = fields.Integer(default=10)
    active = fields.Boolean(default=True)

    _sql_constraints = [
        ('code_unique', 'UNIQUE(code)', 'رمز البند يجب أن يكون فريدًا.'),
    ]

    @api.constrains('fee_type_id', 'kind')
    def _check_fee_type_unique(self):
        for rec in self.filtered('fee_type_id'):
            dup = self.with_context(active_test=False).search_count([
                ('fee_type_id', '=', rec.fee_type_id.id),
                ('kind', '=', 'income'),
                ('id', '!=', rec.id),
            ])
            if dup:
                raise UserError(_(
                    'نوع الرسم "%s" مرتبط ببند إيراد آخر بالفعل — الربط '
                    'المزدوج يضاعف الإيراد في تقرير الموازنة.'
                ) % rec.fee_type_id.name)


class FinanceEntry(models.Model):
    """Manual finance entry: daily expenses, and non-fee income
    (donations, grants, contributions). Fee income is NOT entered here —
    it aggregates automatically from confirmed payments."""
    _name = 'school.finance.entry'
    _description = 'Finance Entry (Expense / Other Income)'
    _inherit = ['mail.thread']
    _order = 'date desc, id desc'
    _rec_name = 'ref'

    ref = fields.Char(
        string='المرجع', required=True, copy=False, readonly=True,
        default=lambda self: _('New')
    )
    date = fields.Date(
        string='التاريخ', required=True, default=fields.Date.today,
        tracking=True
    )
    item_id = fields.Many2one(
        'school.finance.item', string='البند', required=True, tracking=True
    )
    kind = fields.Selection(
        related='item_id.kind', store=True, string='النوع'
    )
    academic_year_id = fields.Many2one(
        'school.academic.year', string='العام الدراسي', required=True,
        index=True,
        default=lambda self: self.env['school.academic.year'].get_active_year()
    )
    currency_id = fields.Many2one(
        'res.currency', default=lambda self: self.env.company.currency_id
    )
    amount = fields.Monetary(
        string='المبلغ', required=True, currency_field='currency_id',
        tracking=True
    )
    memo = fields.Char(string='البيان', required=True)
    attachment = fields.Binary(string='المستند', attachment=True)
    attachment_filename = fields.Char()
    state = fields.Selection([
        ('draft', 'مسودة'),
        ('confirmed', 'مؤكد'),
        ('cancelled', 'ملغي'),
    ], string='الحالة', default='draft', tracking=True)
    confirmed_by = fields.Many2one('res.users', string='أكده', readonly=True,
                                   copy=False)

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get('ref', _('New')) == _('New'):
                vals['ref'] = self.env['ir.sequence'].next_by_code(
                    'school.finance.entry') or _('New')
        return super().create(vals_list)

    @api.constrains('amount')
    def _check_amount(self):
        for rec in self:
            if rec.amount <= 0:
                raise UserError(_('المبلغ يجب أن يكون أكبر من صفر.'))

    def action_confirm(self):
        if not self.env.user.has_group('school_management.group_school_admin'):
            raise UserError(_('تأكيد القيود المالية متاح لمدير النظام فقط.'))
        for rec in self:
            if rec.state == 'draft':
                rec.write({'state': 'confirmed',
                           'confirmed_by': self.env.user.id})

    def action_cancel(self):
        for rec in self:
            if rec.state == 'confirmed' and not self.env.user.has_group(
                    'school_management.group_school_admin'):
                raise UserError(_('إلغاء قيد مؤكد متاح لمدير النظام فقط.'))
            rec.state = 'cancelled'

    def action_draft(self):
        self.write({'state': 'draft'})


class BudgetReport(models.Model):
    """SQL view uniting fee income (confirmed payments mapped through
    fee type → finance item) with confirmed manual entries — feeds the
    budget pivot/graph and the dashboard financial card."""
    _name = 'school.budget.report'
    _description = 'Budget Report (Income vs Expenses)'
    _auto = False
    _order = 'date desc'

    date = fields.Date(string='التاريخ', readonly=True)
    academic_year_id = fields.Many2one(
        'school.academic.year', string='العام الدراسي', readonly=True)
    item_id = fields.Many2one(
        'school.finance.item', string='البند', readonly=True)
    kind = fields.Selection([
        ('income', 'إيراد'),
        ('expense', 'مصروف'),
    ], string='النوع', readonly=True)
    amount = fields.Float(string='المبلغ', readonly=True)
    balance = fields.Float(
        string='الصافي', readonly=True,
        help='Income positive, expenses negative.')

    def init(self):
        tools.drop_view_if_exists(self.env.cr, self._table)
        self.env.cr.execute("""
            CREATE OR REPLACE VIEW %s AS (
                SELECT
                    row_number() OVER (ORDER BY src.date, src.src_id) AS id,
                    src.date,
                    src.academic_year_id,
                    src.item_id,
                    src.kind,
                    src.amount,
                    CASE WHEN src.kind = 'income'
                         THEN src.amount ELSE -src.amount END AS balance
                FROM (
                    SELECT
                        pay.id AS src_id,
                        pay.payment_date AS date,
                        f.academic_year_id AS academic_year_id,
                        COALESCE(
                            fi.id,
                            (SELECT id FROM school_finance_item
                             WHERE code = 'INC-OTHER' LIMIT 1)
                        ) AS item_id,
                        'income' AS kind,
                        pay.amount AS amount
                    FROM school_fee_payment pay
                    JOIN school_fee f ON pay.fee_id = f.id
                    LEFT JOIN school_finance_item fi
                        ON fi.fee_type_id = f.fee_type_id
                        AND fi.kind = 'income'
                    WHERE pay.state = 'confirmed'
                    UNION ALL
                    SELECT
                        1000000 + e.id AS src_id,
                        e.date AS date,
                        e.academic_year_id AS academic_year_id,
                        e.item_id AS item_id,
                        it.kind AS kind,
                        e.amount AS amount
                    FROM school_finance_entry e
                    JOIN school_finance_item it ON e.item_id = it.id
                    WHERE e.state = 'confirmed'
                ) src
            )
        """ % self._table)
