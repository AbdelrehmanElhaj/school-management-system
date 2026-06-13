# -*- coding: utf-8 -*-
from odoo import models, fields, api, _
from odoo.exceptions import ValidationError


class SchoolClass(models.Model):
    _name = 'school.class'
    _description = 'Classroom'
    _inherit = ['mail.thread']
    _order = 'grade_level, name'
    _rec_name = 'display_name'

    name = fields.Char(string='Section', required=True)
    display_name = fields.Char(
        string='Class Name', compute='_compute_display_name', store=True
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
    academic_year_id = fields.Many2one(
        'school.academic.year', string='Academic Year', required=True, tracking=True
    )
    school_id = fields.Many2one(
        'school.branch', string='School',
        related='academic_year_id.school_id', store=True
    )
    teacher_id = fields.Many2one(
        'school.teacher', string='Supervisor Teacher', tracking=True
    )
    student_ids = fields.One2many('school.student', 'class_id', string='Student List')
    student_count = fields.Integer(string='Students', compute='_compute_student_count')
    capacity = fields.Integer(string='Capacity', default=30)
    room = fields.Char(string='Room Number')
    subject_ids = fields.Many2many(
        'school.subject', 'class_subject_rel', 'class_id', 'subject_id',
        string='Subjects'
    )
    state = fields.Selection([
        ('open', 'Open'),
        ('closed', 'Closed'),
    ], string='Status', default='open', tracking=True)
    notes = fields.Text(string='Notes')

    @api.depends('grade_level', 'name')
    def _compute_display_name(self):
        grade_labels = dict(self._fields['grade_level'].selection)
        for rec in self:
            grade = grade_labels.get(rec.grade_level, '')
            rec.display_name = f"{grade} - {rec.name}" if grade and rec.name else rec.name or ''

    @api.depends('student_ids')
    def _compute_student_count(self):
        for rec in self:
            rec.student_count = len(rec.student_ids)

    @api.constrains('student_ids', 'capacity')
    def _check_capacity(self):
        for rec in self:
            if rec.capacity and len(rec.student_ids) > rec.capacity:
                raise ValidationError(
                    _('Class "%s" has exceeded its capacity of %d students.') % (
                        rec.display_name, rec.capacity
                    )
                )

    def action_view_students(self):
        return {
            'type': 'ir.actions.act_window',
            'name': _('Students'),
            'res_model': 'school.student',
            'view_mode': 'tree,form,kanban',
            'domain': [('class_id', '=', self.id)],
            'context': {'default_class_id': self.id},
        }
