# -*- coding: utf-8 -*-
from odoo import models, fields, api, _
from odoo.exceptions import ValidationError


class FeeStructure(models.Model):
    """Fee matrix: year ← grade ← fee type ← amount. The source of truth
    for automatic fee generation at enrollment approval."""
    _name = 'school.fee.structure'
    _description = 'Fee Structure (Grade Fee Matrix)'
    _order = 'academic_year_id desc, grade_level, fee_type_id'
    _rec_name = 'display_name'

    display_name = fields.Char(compute='_compute_display_name', store=True)
    academic_year_id = fields.Many2one(
        'school.academic.year', string='Academic Year', required=True,
        index=True,
        default=lambda self: self.env['school.academic.year'].get_active_year()
    )
    grade_level = fields.Selection([
        ('kg1', 'KG 1'),
        ('kg2', 'KG 2'),
        ('grade1', 'Grade 1'),
        ('grade2', 'Grade 2'),
        ('grade3', 'Grade 3'),
        ('grade4', 'Grade 4'),
        ('grade5', 'Grade 5'),
        ('grade6', 'Grade 6'),
        ('grade7', 'Grade 7'),
        ('grade8', 'Grade 8'),
        ('grade9', 'Grade 9'),
        ('grade10', 'Grade 10'),
        ('grade11', 'Grade 11'),
        ('grade12', 'Grade 12'),
    ], string='Grade Level', required=True)
    fee_type_id = fields.Many2one(
        'school.fee.type', string='Fee Type', required=True
    )
    term = fields.Selection([
        ('first', 'First Term'),
        ('second', 'Second Term'),
        ('third', 'Third Term'),
        ('annual', 'Annual'),
    ], string='Term', required=True, default='annual')
    currency_id = fields.Many2one(
        'res.currency', string='Currency',
        default=lambda self: self.env.company.currency_id
    )
    amount = fields.Monetary(
        string='Amount', required=True, currency_field='currency_id'
    )
    active = fields.Boolean(default=True)

    _sql_constraints = [
        ('year_grade_type_term_unique',
         'UNIQUE(academic_year_id, grade_level, fee_type_id, term)',
         'يوجد بند رسوم لهذا الصف ونوع الرسم والفصل في هذا العام بالفعل.'),
    ]

    @api.depends('academic_year_id', 'grade_level', 'fee_type_id')
    def _compute_display_name(self):
        grade_labels = dict(self._fields['grade_level'].selection)
        for rec in self:
            rec.display_name = '%s / %s / %s' % (
                rec.academic_year_id.name or '',
                grade_labels.get(rec.grade_level, ''),
                rec.fee_type_id.name or '',
            )

    @api.constrains('amount')
    def _check_amount(self):
        for rec in self:
            if rec.amount <= 0:
                raise ValidationError(_('مبلغ بند الرسوم يجب أن يكون أكبر من صفر.'))


class SiblingDiscountRule(models.Model):
    """Sibling discount ladder: N approved children → X% on tuition.
    The highest rule satisfied by the guardian's approved-children count
    in the active year wins."""
    _name = 'school.sibling.discount.rule'
    _description = 'Sibling Discount Rule'
    _order = 'min_siblings'

    name = fields.Char(compute='_compute_name', store=True)
    min_siblings = fields.Integer(
        string='Minimum Children', required=True,
        help='Rule applies when the guardian has at least this many '
             'approved children in the active year.'
    )
    percent = fields.Float(string='Discount %', required=True)
    active = fields.Boolean(default=True)

    _sql_constraints = [
        ('min_siblings_unique', 'UNIQUE(min_siblings)',
         'توجد قاعدة خصم لنفس عدد الأبناء بالفعل.'),
    ]

    @api.depends('min_siblings', 'percent')
    def _compute_name(self):
        for rec in self:
            rec.name = _('%(n)d أبناء فأكثر ← %(p).0f%%',
                         n=rec.min_siblings, p=rec.percent)

    @api.constrains('min_siblings', 'percent')
    def _check_values(self):
        for rec in self:
            if rec.min_siblings < 2:
                raise ValidationError(
                    _('خصم الأشقاء يبدأ من طفلين على الأقل.'))
            if not (0 < rec.percent <= 100):
                raise ValidationError(_('النسبة يجب أن تكون بين 0 و100.'))

    @api.model
    def get_percent_for_count(self, count):
        rule = self.search([('min_siblings', '<=', count)],
                           order='min_siblings desc', limit=1)
        return rule.percent or 0.0


class FeeStructureCopyWizard(models.TransientModel):
    _name = 'school.fee.structure.copy.wizard'
    _description = 'Copy Fee Structure From a Previous Year'

    source_year_id = fields.Many2one(
        'school.academic.year', string='نسخ مصفوفة عام', required=True
    )
    target_year_id = fields.Many2one(
        'school.academic.year', string='إلى عام', required=True,
        domain="[('id', '!=', source_year_id)]"
    )

    def action_copy(self):
        self.ensure_one()
        source = self.env['school.fee.structure'].search([
            ('academic_year_id', '=', self.source_year_id.id)])
        existing = self.env['school.fee.structure'].with_context(
            active_test=False).search([
                ('academic_year_id', '=', self.target_year_id.id)])
        keys = {(r.grade_level, r.fee_type_id.id, r.term) for r in existing}
        vals = [{
            'academic_year_id': self.target_year_id.id,
            'grade_level': r.grade_level,
            'fee_type_id': r.fee_type_id.id,
            'term': r.term,
            'amount': r.amount,
        } for r in source if (r.grade_level, r.fee_type_id.id, r.term) not in keys]
        self.env['school.fee.structure'].create(vals)
        return {'type': 'ir.actions.act_window_close'}
