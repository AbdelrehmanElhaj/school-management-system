# -*- coding: utf-8 -*-
from odoo import models, fields, api, _


class StudentEnrollment(models.Model):
    """One enrollment record per student per academic year.

    student.class_id stays the "current situation"; the full history lives
    here, so a continuing student is promoted without duplicating his card
    and without touching any past-year record.
    """
    _name = 'school.student.enrollment'
    _description = 'Student Yearly Enrollment'
    _order = 'academic_year_id desc, student_id'
    _rec_name = 'display_name'

    display_name = fields.Char(
        string='Reference', compute='_compute_display_name', store=True
    )
    student_id = fields.Many2one(
        'school.student', string='Student', required=True,
        ondelete='cascade', index=True
    )
    academic_year_id = fields.Many2one(
        'school.academic.year', string='Academic Year',
        required=True, index=True
    )
    year_state = fields.Selection(
        related='academic_year_id.state', string='Year Status', store=True
    )
    class_id = fields.Many2one('school.class', string='Class')
    grade_level = fields.Selection(
        [
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
        ],
        string='Grade Level',
        help='Snapshot of the class grade at enrollment time.'
    )
    state = fields.Selection([
        ('enrolled', 'ملتحق'),
        ('promoted', 'مُرحَّل'),
        ('withdrawn', 'منسحب'),
        ('graduated', 'متخرج'),
    ], string='Status', default='enrolled', required=True)
    enrollment_date = fields.Date(
        string='Enrollment Date', default=fields.Date.today
    )
    notes = fields.Char(string='Notes')

    _sql_constraints = [
        ('student_year_unique', 'UNIQUE(student_id, academic_year_id)',
         'الطالب مسجَّل بالفعل في هذا العام الدراسي — لا يمكن تكرار سجل الالتحاق.'),
    ]

    @api.depends('student_id', 'academic_year_id')
    def _compute_display_name(self):
        for rec in self:
            rec.display_name = '%s / %s' % (
                rec.student_id.name or '', rec.academic_year_id.name or ''
            )

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            # Snapshot the grade from the class at creation time.
            if vals.get('class_id') and not vals.get('grade_level'):
                vals['grade_level'] = self.env['school.class'].browse(
                    vals['class_id']).grade_level
        return super().create(vals_list)

    @api.onchange('class_id')
    def _onchange_class_id(self):
        if self.class_id:
            self.grade_level = self.class_id.grade_level
            self.academic_year_id = self.class_id.academic_year_id
