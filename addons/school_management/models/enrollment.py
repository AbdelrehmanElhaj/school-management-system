# -*- coding: utf-8 -*-
from odoo import models, fields, api, _


class EnrollmentRequirement(models.Model):
    _name = 'school.enrollment.requirement'
    _description = 'Enrollment Requirement'
    _order = 'sequence, name'

    name = fields.Char(string='Requirement', required=True, translate=True)
    description = fields.Text(string='Description', translate=True)
    is_required = fields.Boolean(string='Required', default=True)
    sequence = fields.Integer(string='Sequence', default=10)
    active = fields.Boolean(string='Active', default=True)


class EnrollmentChecklistItem(models.Model):
    _name = 'school.enrollment.checklist.item'
    _description = 'Student Enrollment Checklist Item'
    _order = 'requirement_id'

    student_id = fields.Many2one(
        'school.student', string='Student', required=True, ondelete='cascade'
    )
    requirement_id = fields.Many2one(
        'school.enrollment.requirement', string='Requirement',
        required=True, ondelete='restrict'
    )
    requirement_name = fields.Char(
        related='requirement_id.name', string='Requirement', readonly=True, store=True
    )
    is_required = fields.Boolean(
        related='requirement_id.is_required', string='Required', readonly=True
    )
    status = fields.Selection([
        ('pending', 'قيد الانتظار'),
        ('submitted', 'مُقدَّم'),
        ('verified', 'مُوثَّق'),
        ('not_applicable', 'لا ينطبق'),
    ], string='Status', default='pending', required=True)
    document_file = fields.Binary(string='Document', attachment=True)
    document_filename = fields.Char(string='Filename')
    notes = fields.Char(string='Notes')
