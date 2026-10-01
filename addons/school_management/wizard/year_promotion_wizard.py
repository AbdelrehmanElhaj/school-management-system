# -*- coding: utf-8 -*-
from odoo import models, fields, api, _
from odoo.exceptions import UserError

# Promotion order of grade levels; grade12 students graduate instead.
GRADE_SEQUENCE = [
    'kg1', 'kg2',
    'grade1', 'grade2', 'grade3', 'grade4', 'grade5', 'grade6',
    'grade7', 'grade8', 'grade9', 'grade10', 'grade11', 'grade12',
]


class YearPromotionWizard(models.TransientModel):
    _name = 'school.year.promotion.wizard'
    _description = 'Promote Students to New Academic Year'

    source_year_id = fields.Many2one(
        'school.academic.year', string='من العام الدراسي', required=True,
        default=lambda self: self.env['school.academic.year'].get_active_year()
    )
    target_year_id = fields.Many2one(
        'school.academic.year', string='إلى العام الدراسي', required=True,
        domain="[('id', '!=', source_year_id), ('state', 'in', ['draft', 'active'])]"
    )
    line_ids = fields.One2many(
        'school.year.promotion.wizard.line', 'wizard_id', string='الطلاب'
    )
    line_count = fields.Integer(compute='_compute_line_count')

    @api.depends('line_ids')
    def _compute_line_count(self):
        for rec in self:
            rec.line_count = len(rec.line_ids.filtered('include'))

    def _suggest_target_class(self, source_class):
        """Suggest the target-year class of the next grade, preferring the
        same section name."""
        self.ensure_one()
        if source_class.grade_level not in GRADE_SEQUENCE:
            return self.env['school.class'], False
        idx = GRADE_SEQUENCE.index(source_class.grade_level)
        if idx + 1 >= len(GRADE_SEQUENCE):
            return self.env['school.class'], True  # graduating
        next_grade = GRADE_SEQUENCE[idx + 1]
        candidates = self.env['school.class'].search([
            ('academic_year_id', '=', self.target_year_id.id),
            ('grade_level', '=', next_grade),
        ])
        same_section = candidates.filtered(
            lambda c: c.name == source_class.name)
        return (same_section[:1] or candidates[:1]), False

    def action_load_students(self):
        """Fill the lines with the source year's active students and a
        suggested target class for each."""
        self.ensure_one()
        if self.source_year_id == self.target_year_id:
            raise UserError(_('عام المصدر وعام الهدف لا يمكن أن يكونا نفس العام.'))
        self.line_ids.unlink()
        students = self.env['school.student'].search([
            ('class_id.academic_year_id', '=', self.source_year_id.id),
            ('status', '=', 'active'),
            ('enrollment_state', '=', 'active'),
        ])
        lines = []
        for student in students:
            target_class, graduating = self._suggest_target_class(
                student.class_id)
            lines.append({
                'wizard_id': self.id,
                'student_id': student.id,
                'source_class_id': student.class_id.id,
                'target_class_id': target_class.id,
                'graduating': graduating,
                'include': not graduating,
            })
        self.env['school.year.promotion.wizard.line'].create(lines)
        return {
            'type': 'ir.actions.act_window',
            'res_model': self._name,
            'res_id': self.id,
            'view_mode': 'form',
            'target': 'new',
        }

    def action_promote(self):
        """Create the new-year enrollment record and move each included
        student to his target class — without touching any historical
        financial or academic record."""
        self.ensure_one()
        if self.target_year_id.state == 'done':
            raise UserError(_('لا يمكن الترحيل إلى عام مؤرشف.'))
        lines = self.line_ids.filtered('include')
        if not lines:
            raise UserError(_('لا يوجد طلاب محددون للترحيل. '
                              'استخدم زر «تحميل الطلاب» أولًا.'))
        missing = lines.filtered(
            lambda l: not l.target_class_id and not l.graduating)
        if missing:
            raise UserError(_(
                'لا يوجد فصل هدف للطلاب التالين (أنشئ فصول العام الجديد أولًا): %s'
            ) % ', '.join(missing.mapped('student_id.name')[:10]))
        Enrollment = self.env['school.student.enrollment']
        promoted = graduated = skipped = 0
        for line in lines:
            student = line.student_id
            if Enrollment.search_count([
                ('student_id', '=', student.id),
                ('academic_year_id', '=', self.target_year_id.id),
            ]):
                skipped += 1
                continue
            # Mark the source-year enrollment as promoted/graduated.
            source_enrollment = Enrollment.search([
                ('student_id', '=', student.id),
                ('academic_year_id', '=', self.source_year_id.id),
            ], limit=1)
            if line.graduating:
                if source_enrollment:
                    source_enrollment.state = 'graduated'
                student.write({'status': 'graduated', 'class_id': False})
                student.message_post(body=_(
                    'تخرَّج الطالب بنهاية العام %s.') % self.source_year_id.name)
                graduated += 1
                continue
            if source_enrollment and source_enrollment.state == 'enrolled':
                source_enrollment.state = 'promoted'
            Enrollment.create({
                'student_id': student.id,
                'academic_year_id': self.target_year_id.id,
                'class_id': line.target_class_id.id,
                'state': 'enrolled',
            })
            student.write({'class_id': line.target_class_id.id})
            student.message_post(body=_(
                'رُحِّل الطالب من %(src)s إلى %(dst)s (العام %(year)s).',
                src=line.source_class_id.display_name,
                dst=line.target_class_id.display_name,
                year=self.target_year_id.name,
            ))
            promoted += 1
        message = _('اكتمل الترحيل: %(p)d مُرحَّل، %(g)d متخرج، %(s)d مُتخطَّى '
                    '(مسجَّل مسبقًا في عام الهدف).',
                    p=promoted, g=graduated, s=skipped)
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': _('ترحيل الطلاب'),
                'message': message,
                'type': 'success',
                'sticky': True,
            },
        }


class YearPromotionWizardLine(models.TransientModel):
    _name = 'school.year.promotion.wizard.line'
    _description = 'Promotion Wizard Line'
    _order = 'source_class_id, student_id'

    wizard_id = fields.Many2one(
        'school.year.promotion.wizard', required=True, ondelete='cascade'
    )
    include = fields.Boolean(string='ترحيل', default=True)
    student_id = fields.Many2one(
        'school.student', string='الطالب', required=True
    )
    source_class_id = fields.Many2one(
        'school.class', string='الفصل الحالي', readonly=True
    )
    target_class_id = fields.Many2one(
        'school.class', string='الفصل الجديد',
        domain="[('academic_year_id', '=', parent.target_year_id)]"
    )
    graduating = fields.Boolean(string='متخرج', readonly=True)
