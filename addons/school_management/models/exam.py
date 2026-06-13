# -*- coding: utf-8 -*-
from odoo import models, fields, api, _
from odoo.exceptions import ValidationError


class Exam(models.Model):
    _name = 'school.exam'
    _description = 'Exam'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'date desc'
    _rec_name = 'name'

    name = fields.Char(string='Exam Name', required=True, tracking=True)
    exam_type = fields.Selection([
        ('midterm', 'Midterm'),
        ('final', 'Final'),
        ('quiz', 'Quiz'),
        ('assignment', 'Assignment'),
        ('practical', 'Practical'),
    ], string='Type', required=True, default='quiz', tracking=True)
    term = fields.Selection([
        ('first', 'First Term'),
        ('second', 'Second Term'),
        ('third', 'Third Term'),
        ('annual', 'Annual'),
    ], string='Term', required=True, default='first', tracking=True)
    subject_id = fields.Many2one(
        'school.subject', string='Subject', required=True, tracking=True
    )
    class_id = fields.Many2one(
        'school.class', string='Class', required=True, tracking=True
    )
    academic_year_id = fields.Many2one(
        'school.academic.year', string='Academic Year',
        related='class_id.academic_year_id', store=True
    )
    date = fields.Date(string='Exam Date', required=True, tracking=True)
    max_score = fields.Float(string='Maximum Score', required=True, default=100.0)
    pass_score = fields.Float(string='Pass Score', default=50.0)
    teacher_id = fields.Many2one(
        'school.teacher', string='Teacher', tracking=True
    )
    state = fields.Selection([
        ('draft', 'Draft'),
        ('confirmed', 'Confirmed'),
        ('graded', 'Graded'),
        ('closed', 'Closed'),
    ], string='Status', default='draft', tracking=True)
    grade_ids = fields.One2many('school.grade', 'exam_id', string='Grades')
    grade_count = fields.Integer(string='Grades', compute='_compute_grade_count')
    description = fields.Text(string='Description')

    @api.depends('grade_ids')
    def _compute_grade_count(self):
        for rec in self:
            rec.grade_count = len(rec.grade_ids)

    @api.constrains('max_score', 'pass_score')
    def _check_scores(self):
        for rec in self:
            if rec.max_score <= 0:
                raise ValidationError(_('Maximum score must be greater than 0.'))
            if rec.pass_score < 0 or rec.pass_score > rec.max_score:
                raise ValidationError(
                    _('Pass score must be between 0 and the maximum score.')
                )

    def action_confirm(self):
        self.write({'state': 'confirmed'})

    def action_grade(self):
        self.write({'state': 'graded'})

    def action_close(self):
        self.write({'state': 'closed'})

    def action_draft(self):
        self.write({'state': 'draft'})

    def action_view_grades(self):
        return {
            'type': 'ir.actions.act_window',
            'name': _('Grades'),
            'res_model': 'school.grade',
            'view_mode': 'tree,form',
            'domain': [('exam_id', '=', self.id)],
            'context': {
                'default_exam_id': self.id,
                'default_class_id': self.class_id.id,
                'default_subject_id': self.subject_id.id,
            },
        }

    def action_enter_grades(self):
        """Open bulk grade entry wizard."""
        return {
            'type': 'ir.actions.act_window',
            'name': _('Enter Grades'),
            'res_model': 'school.grade.bulk',
            'view_mode': 'form',
            'target': 'new',
            'context': {
                'default_exam_id': self.id,
                'default_class_id': self.class_id.id,
            },
        }
