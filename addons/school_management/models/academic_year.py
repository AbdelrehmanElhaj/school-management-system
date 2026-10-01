# -*- coding: utf-8 -*-
from odoo import models, fields, api, _
from odoo.exceptions import ValidationError


class AcademicYear(models.Model):
    _name = 'school.academic.year'
    _description = 'Academic Year'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'date_start desc'
    _rec_name = 'name'

    name = fields.Char(string='Academic Year', required=True, translate=True)
    code = fields.Char(string='Code', required=True)
    school_id = fields.Many2one(
        'school.branch', string='School / Campus', ondelete='restrict', tracking=True
    )
    date_start = fields.Date(string='Start Date', required=True)
    date_end = fields.Date(string='End Date', required=True)
    state = fields.Selection([
        ('draft', 'Draft'),
        ('active', 'Active'),
        ('done', 'Closed'),
    ], string='Status', default='draft', tracking=True)
    current = fields.Boolean(string='Current Year', default=False)
    class_ids = fields.One2many('school.class', 'academic_year_id', string='Class List')
    class_count = fields.Integer(string='Classes', compute='_compute_class_count')
    notes = fields.Text(string='Notes')

    _sql_constraints = [
        ('code_unique', 'UNIQUE(code)', 'Academic year code must be unique.'),
    ]

    @api.depends('class_ids')
    def _compute_class_count(self):
        for rec in self:
            rec.class_count = len(rec.class_ids)

    @api.constrains('date_start', 'date_end')
    def _check_dates(self):
        for rec in self:
            if rec.date_start and rec.date_end and rec.date_start >= rec.date_end:
                raise ValidationError(_('End date must be after start date.'))

    @api.model
    def get_active_year(self, school=None):
        """Return the single active academic year (used as default everywhere)."""
        domain = [('state', '=', 'active'), ('current', '=', True)]
        if school:
            domain.append(('school_id', '=', school.id))
        year = self.search(domain, limit=1)
        if not year:
            year = self.search([('state', '=', 'active')],
                               order='date_start desc', limit=1)
        return year

    def action_activate(self):
        # Only one active year per school at a time
        domain = [('current', '=', True)]
        if self.school_id:
            domain.append(('school_id', '=', self.school_id.id))
        self.search(domain).write({'current': False})
        self.write({'state': 'active', 'current': True})

    def action_close(self):
        return self.action_archive_year()

    def action_archive_year(self):
        """Archive the year: validate nothing is half-done, then close it and
        all its classes. Archived (done) years are locked by record rules."""
        for rec in self:
            draft_fees = self.env['school.fee'].search_count([
                ('academic_year_id', '=', rec.id), ('state', '=', 'draft'),
            ])
            if draft_fees:
                raise ValidationError(_(
                    'لا يمكن أرشفة العام "%s": يوجد %d رسم في حالة مسودة. '
                    'يجب تأكيدها أو إلغاؤها أولًا.') % (rec.name, draft_fees))
            draft_payments = self.env['school.fee.payment'].search_count([
                ('fee_id.academic_year_id', '=', rec.id), ('state', '=', 'draft'),
            ])
            if draft_payments:
                raise ValidationError(_(
                    'لا يمكن أرشفة العام "%s": يوجد %d دفعة غير مؤكدة. '
                    'يجب تأكيدها أو إلغاؤها أولًا.') % (rec.name, draft_payments))
            rec.class_ids.filtered(lambda c: c.state == 'open').write(
                {'state': 'closed'})
            rec.write({'state': 'done', 'current': False})
            rec.message_post(body=_('تمت أرشفة العام الدراسي وإغلاق جميع فصوله.'))
        return True

    def action_draft(self):
        self.write({'state': 'draft'})

    def action_view_classes(self):
        return {
            'type': 'ir.actions.act_window',
            'name': _('Classes'),
            'res_model': 'school.class',
            'view_mode': 'tree,form',
            'domain': [('academic_year_id', '=', self.id)],
            'context': {'default_academic_year_id': self.id},
        }
