# -*- coding: utf-8 -*-
from odoo import models, fields, api, _
from odoo.exceptions import ValidationError


class Grade(models.Model):
    _name = 'school.grade'
    _description = 'Student Grade'
    _inherit = ['mail.thread']
    _order = 'exam_id, student_id'
    _rec_name = 'display_name'

    display_name = fields.Char(
        string='Reference', compute='_compute_display_name', store=True
    )
    student_id = fields.Many2one(
        'school.student', string='Student', required=True,
        domain=[('status', '=', 'active')]
    )
    exam_id = fields.Many2one(
        'school.exam', string='Exam', required=True, tracking=True
    )
    subject_id = fields.Many2one(
        'school.subject', string='Subject',
        related='exam_id.subject_id', store=True
    )
    class_id = fields.Many2one(
        'school.class', string='Class',
        related='exam_id.class_id', store=True
    )
    academic_year_id = fields.Many2one(
        'school.academic.year', string='Academic Year',
        related='exam_id.academic_year_id', store=True
    )
    school_id = fields.Many2one(
        'school.branch', string='School',
        related='class_id.school_id', store=True
    )
    term = fields.Selection(
        related='exam_id.term', store=True, string='Term'
    )
    score = fields.Float(string='Score', required=True, default=0.0, tracking=True)
    max_score = fields.Float(
        string='Max Score', related='exam_id.max_score', store=True
    )
    pass_score = fields.Float(
        string='Pass Score', related='exam_id.pass_score', store=True
    )
    percentage = fields.Float(
        string='Percentage (%)', compute='_compute_percentage', store=True, digits=(5, 2)
    )
    grade_letter = fields.Char(
        string='Grade', compute='_compute_grade_letter', store=True
    )
    passed = fields.Boolean(
        string='Passed', compute='_compute_passed', store=True
    )
    passed_display = fields.Char(
        string='Result', compute='_compute_passed_display'
    )
    rank = fields.Integer(
        string='Rank', compute='_compute_rank', store=True
    )
    notes = fields.Text(string='Notes')

    _sql_constraints = [
        ('student_exam_unique', 'UNIQUE(student_id, exam_id)',
         'Grade already exists for this student in this exam.'),
    ]

    @api.depends('student_id', 'exam_id')
    def _compute_display_name(self):
        for rec in self:
            student = rec.student_id.name or ''
            exam = rec.exam_id.name or ''
            rec.display_name = f"{student} / {exam}" if student and exam else student or exam

    @api.depends('score', 'max_score')
    def _compute_percentage(self):
        for rec in self:
            if rec.max_score:
                rec.percentage = (rec.score / rec.max_score) * 100
            else:
                rec.percentage = 0.0

    @api.depends('percentage')
    def _compute_grade_letter(self):
        for rec in self:
            pct = rec.percentage
            if pct >= 95:
                rec.grade_letter = 'A+'
            elif pct >= 90:
                rec.grade_letter = 'A'
            elif pct >= 85:
                rec.grade_letter = 'B+'
            elif pct >= 80:
                rec.grade_letter = 'B'
            elif pct >= 75:
                rec.grade_letter = 'C+'
            elif pct >= 70:
                rec.grade_letter = 'C'
            elif pct >= 65:
                rec.grade_letter = 'D+'
            elif pct >= 60:
                rec.grade_letter = 'D'
            else:
                rec.grade_letter = 'F'

    @api.depends('score', 'pass_score')
    def _compute_passed(self):
        for rec in self:
            rec.passed = rec.score >= rec.pass_score

    @api.depends('passed')
    def _compute_passed_display(self):
        for rec in self:
            rec.passed_display = _('Pass') if rec.passed else _('Fail')

    @api.depends('exam_id', 'score')
    def _compute_rank(self):
        # Rank within the same exam, ordered by score descending
        exams = self.mapped('exam_id')
        for exam in exams:
            grades = self.env['school.grade'].search(
                [('exam_id', '=', exam.id)], order='score desc'
            )
            for rank, grade in enumerate(grades, start=1):
                if grade in self:
                    grade.rank = rank

    @api.constrains('score', 'max_score')
    def _check_score(self):
        for rec in self:
            if rec.score < 0:
                raise ValidationError(_('Score cannot be negative.'))
            if rec.max_score and rec.score > rec.max_score:
                raise ValidationError(
                    _('Score (%s) cannot exceed maximum score (%s).') % (
                        rec.score, rec.max_score
                    )
                )


class GradeBulk(models.TransientModel):
    """Wizard to enter grades for all students in an exam at once."""
    _name = 'school.grade.bulk'
    _description = 'Bulk Grade Entry Wizard'

    exam_id = fields.Many2one('school.exam', string='Exam', required=True)
    class_id = fields.Many2one(
        'school.class', string='Class',
        related='exam_id.class_id', readonly=True
    )
    line_ids = fields.One2many(
        'school.grade.bulk.line', 'wizard_id', string='Students'
    )

    @api.onchange('exam_id')
    def _onchange_exam(self):
        if self.exam_id and self.exam_id.class_id:
            lines = [(5, 0, 0)]
            existing = {
                g.student_id.id: g.score
                for g in self.env['school.grade'].search(
                    [('exam_id', '=', self.exam_id.id)]
                )
            }
            for student in self.exam_id.class_id.student_ids.filtered(
                lambda s: s.status == 'active'
            ):
                lines.append((0, 0, {
                    'student_id': student.id,
                    'score': existing.get(student.id, 0.0),
                }))
            self.line_ids = lines

    def action_confirm(self):
        Grade = self.env['school.grade']
        for line in self.line_ids:
            existing = Grade.search([
                ('student_id', '=', line.student_id.id),
                ('exam_id', '=', self.exam_id.id),
            ])
            if existing:
                existing.write({'score': line.score, 'notes': line.notes})
            else:
                Grade.create({
                    'student_id': line.student_id.id,
                    'exam_id': self.exam_id.id,
                    'score': line.score,
                    'notes': line.notes,
                })
        # Mark exam as graded
        self.exam_id.write({'state': 'graded'})
        return {'type': 'ir.actions.act_window_close'}


class GradeBulkLine(models.TransientModel):
    _name = 'school.grade.bulk.line'
    _description = 'Bulk Grade Entry Line'

    wizard_id = fields.Many2one('school.grade.bulk', string='Wizard')
    student_id = fields.Many2one('school.student', string='Student', required=True)
    score = fields.Float(string='Score', default=0.0)
    notes = fields.Char(string='Notes')
