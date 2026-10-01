# -*- coding: utf-8 -*-
from odoo import models, fields, _
from odoo.exceptions import UserError


class ClassCopyWizard(models.TransientModel):
    """Create the new year's classes in one click by copying the structure
    (grade, section, capacity, subjects) of a previous year."""
    _name = 'school.class.copy.wizard'
    _description = 'Copy Class Structure to a New Year'

    source_year_id = fields.Many2one(
        'school.academic.year', string='نسخ فصول العام', required=True,
        default=lambda self: self.env['school.academic.year'].get_active_year()
    )
    target_year_id = fields.Many2one(
        'school.academic.year', string='إلى العام', required=True,
        domain="[('id', '!=', source_year_id), ('state', 'in', ['draft', 'active'])]"
    )
    copy_teachers = fields.Boolean(string='نسخ المعلمين المشرفين', default=False)

    def action_copy(self):
        self.ensure_one()
        if self.source_year_id == self.target_year_id:
            raise UserError(_('عام المصدر وعام الهدف لا يمكن أن يكونا نفس العام.'))
        source_classes = self.env['school.class'].search([
            ('academic_year_id', '=', self.source_year_id.id),
        ])
        if not source_classes:
            raise UserError(_('لا توجد فصول في عام المصدر.'))
        existing = self.env['school.class'].search([
            ('academic_year_id', '=', self.target_year_id.id),
        ])
        existing_keys = {(c.grade_level, c.name) for c in existing}
        vals_list = []
        for cls in source_classes:
            if (cls.grade_level, cls.name) in existing_keys:
                continue
            vals_list.append({
                'name': cls.name,
                'grade_level': cls.grade_level,
                'academic_year_id': self.target_year_id.id,
                'capacity': cls.capacity,
                'room': cls.room,
                'subject_ids': [(6, 0, cls.subject_ids.ids)],
                'teacher_id': cls.teacher_id.id if self.copy_teachers else False,
            })
        created = self.env['school.class'].create(vals_list)
        return {
            'type': 'ir.actions.act_window',
            'name': _('فصول العام %s') % self.target_year_id.name,
            'res_model': 'school.class',
            'view_mode': 'tree,form',
            'domain': [('academic_year_id', '=', self.target_year_id.id)],
            'context': {'default_academic_year_id': self.target_year_id.id},
        } if created or existing else {'type': 'ir.actions.act_window_close'}
