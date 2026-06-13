# -*- coding: utf-8 -*-
from odoo import models, fields, api, _
from odoo.exceptions import ValidationError
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
    school_id = fields.Many2one(
        'school.branch', string='School',
        related='class_id.school_id', store=True
    )
    enrollment_date = fields.Date(string='Enrollment Date', default=fields.Date.today)
    status = fields.Selection([
        ('active', 'Active'),
        ('withdrawn', 'Withdrawn'),
        ('transferred', 'Transferred'),
        ('graduated', 'Graduated'),
    ], string='Status', default='active', tracking=True)

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

    _sql_constraints = [
        ('student_code_unique', 'UNIQUE(student_code)', 'Student ID must be unique.'),
    ]

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get('student_code', _('New')) == _('New'):
                vals['student_code'] = self.env['ir.sequence'].next_by_code(
                    'school.student') or _('New')
        return super().create(vals_list)

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

    @api.constrains('birth_date')
    def _check_birth_date(self):
        for rec in self:
            if rec.birth_date and rec.birth_date > date.today():
                raise ValidationError(_('Birth date cannot be in the future.'))

    def action_withdraw(self):
        self.write({'status': 'withdrawn'})

    def action_activate(self):
        self.write({'status': 'active'})

    def action_transfer(self):
        self.write({'status': 'transferred'})


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
    user_id = fields.Many2one('res.users', string='Portal User')
    notes = fields.Text(string='Notes')

    @api.depends('student_ids')
    def _compute_student_count(self):
        for rec in self:
            rec.student_count = len(rec.student_ids)

    def action_view_students(self):
        return {
            'type': 'ir.actions.act_window',
            'name': _('Children'),
            'res_model': 'school.student',
            'view_mode': 'tree,form',
            'domain': [('guardian_id', '=', self.id)],
            'context': {'default_guardian_id': self.id},
        }
