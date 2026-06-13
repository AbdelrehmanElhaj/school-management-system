# -*- coding: utf-8 -*-
from odoo import models, fields, api, _
from odoo.exceptions import ValidationError


class Subject(models.Model):
    _name = 'school.subject'
    _description = 'Subject'
    _order = 'name'

    name = fields.Char(string='Subject Name', required=True, translate=True)
    code = fields.Char(string='Code', required=True)
    description = fields.Text(string='Description')
    teacher_ids = fields.Many2many('school.teacher', string='Teachers')

    _sql_constraints = [
        ('code_unique', 'UNIQUE(code)', 'Subject code must be unique.'),
    ]


class Teacher(models.Model):
    _name = 'school.teacher'
    _description = 'Teacher'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'name'
    _rec_name = 'name'

    name = fields.Char(string='Full Name', required=True, tracking=True)
    employee_code = fields.Char(
        string='Employee ID', required=True, copy=False,
        default=lambda self: _('New'), tracking=True
    )
    gender = fields.Selection([
        ('male', 'Male'),
        ('female', 'Female'),
    ], string='Gender', required=True, default='male')
    birth_date = fields.Date(string='Date of Birth')
    nationality = fields.Many2one('res.country', string='Nationality')
    national_id = fields.Char(string='National ID')
    photo = fields.Binary(string='Photo', attachment=True)

    school_id = fields.Many2one(
        'school.branch', string='School / Campus', ondelete='restrict', tracking=True
    )

    # Professional Information
    specialization = fields.Char(string='Specialization', required=True)
    qualification = fields.Char(string='Qualification')
    hire_date = fields.Date(string='Hire Date', default=fields.Date.today)
    subject_ids = fields.Many2many(
        'school.subject', 'teacher_subject_rel', 'teacher_id', 'subject_id',
        string='Subjects'
    )
    class_ids = fields.Many2many(
        'school.class', 'teacher_class_rel', 'teacher_id', 'class_id',
        string='Assigned Classes'
    )
    class_count = fields.Integer(string='Classes', compute='_compute_class_count')

    # Contact
    email = fields.Char(string='Email')
    phone = fields.Char(string='Phone')
    mobile = fields.Char(string='Mobile')
    address = fields.Text(string='Address')

    # System User
    user_id = fields.Many2one('res.users', string='System User')
    status = fields.Selection([
        ('active', 'Active'),
        ('inactive', 'Inactive'),
    ], string='Status', default='active', tracking=True)
    notes = fields.Text(string='Notes')

    _sql_constraints = [
        ('employee_code_unique', 'UNIQUE(employee_code)', 'Employee ID must be unique.'),
    ]

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get('employee_code', _('New')) == _('New'):
                vals['employee_code'] = self.env['ir.sequence'].next_by_code(
                    'school.teacher') or _('New')
        return super().create(vals_list)

    @api.depends('class_ids')
    def _compute_class_count(self):
        for rec in self:
            rec.class_count = len(rec.class_ids)

    def action_view_classes(self):
        return {
            'type': 'ir.actions.act_window',
            'name': _('Classes'),
            'res_model': 'school.class',
            'view_mode': 'tree,form',
            'domain': [('teacher_id', '=', self.id)],
        }
