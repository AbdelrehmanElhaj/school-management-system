# -*- coding: utf-8 -*-
from odoo import models, fields, api, _


class SchoolBranch(models.Model):
    _name = 'school.branch'
    _description = 'School Branch / Campus'
    _inherit = ['mail.thread']
    _order = 'name'

    name = fields.Char(string='School Name', required=True, tracking=True)
    code = fields.Char(string='Code', required=True)
    logo = fields.Binary(string='Logo', attachment=True)
    address = fields.Text(string='Address')
    phone = fields.Char(string='Phone')
    email = fields.Char(string='Email')
    website = fields.Char(string='Website')
    principal_id = fields.Many2one(
        'school.teacher', string='Principal', tracking=True
    )
    active = fields.Boolean(default=True)
    notes = fields.Text(string='Notes')

    # ── Stats ─────────────────────────────────────────────────────────────────
    student_count = fields.Integer(
        string='Students', compute='_compute_stats'
    )
    teacher_count = fields.Integer(
        string='Teachers', compute='_compute_stats'
    )
    class_count = fields.Integer(
        string='Classes', compute='_compute_stats'
    )

    _sql_constraints = [
        ('code_unique', 'UNIQUE(code)', 'School code must be unique.'),
    ]

    @api.depends_context('uid')
    def _compute_stats(self):
        for branch in self:
            branch.student_count = self.env['school.student'].search_count([
                ('school_id', '=', branch.id), ('status', '=', 'active'),
            ])
            branch.teacher_count = self.env['school.teacher'].search_count([
                ('school_id', '=', branch.id), ('status', '=', 'active'),
            ])
            branch.class_count = self.env['school.class'].search_count([
                ('school_id', '=', branch.id), ('state', '=', 'open'),
            ])

    def action_view_students(self):
        return {
            'type': 'ir.actions.act_window',
            'name': _('Students'),
            'res_model': 'school.student',
            'view_mode': 'tree,form',
            'domain': [('school_id', '=', self.id)],
        }

    def action_view_teachers(self):
        return {
            'type': 'ir.actions.act_window',
            'name': _('Teachers'),
            'res_model': 'school.teacher',
            'view_mode': 'tree,form',
            'domain': [('school_id', '=', self.id)],
        }

    def action_view_classes(self):
        return {
            'type': 'ir.actions.act_window',
            'name': _('Classes'),
            'res_model': 'school.class',
            'view_mode': 'tree,form',
            'domain': [('school_id', '=', self.id)],
        }
