# -*- coding: utf-8 -*-
from odoo import models, fields, api, _
from odoo.exceptions import ValidationError


DAY_SELECTION = [
    ('0', 'Sunday'),
    ('1', 'Monday'),
    ('2', 'Tuesday'),
    ('3', 'Wednesday'),
    ('4', 'Thursday'),
    ('5', 'Friday'),
    ('6', 'Saturday'),
]
DAY_ORDER = ['0', '1', '2', '3', '4']
DAY_LABELS = dict(DAY_SELECTION)


def _float_to_hhmm(v):
    h = int(v)
    m = round((v - h) * 60)
    return f"{h:02d}:{m:02d}"


class SchoolPeriod(models.Model):
    _name = 'school.period'
    _description = 'School Period'
    _order = 'sequence'

    name = fields.Char(string='Period Name', required=True, translate=True)
    sequence = fields.Integer(default=10)
    time_start = fields.Float(string='Start Time', required=True)
    time_end = fields.Float(string='End Time', required=True)
    time_start_display = fields.Char(
        string='Start', compute='_compute_time_display', store=False
    )
    time_end_display = fields.Char(
        string='End', compute='_compute_time_display', store=False
    )
    is_break = fields.Boolean(string='Break / Recess')
    active = fields.Boolean(default=True)

    @api.depends('time_start', 'time_end')
    def _compute_time_display(self):
        for rec in self:
            rec.time_start_display = _float_to_hhmm(rec.time_start)
            rec.time_end_display = _float_to_hhmm(rec.time_end)

    @api.constrains('time_start', 'time_end')
    def _check_times(self):
        for rec in self:
            if rec.time_end <= rec.time_start:
                raise ValidationError(_('End time must be after start time.'))


class SchoolTimetable(models.Model):
    _name = 'school.timetable'
    _description = 'Class Timetable'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'academic_year_id desc, class_id'
    _rec_name = 'display_name'

    name = fields.Char(string='Reference', required=True)
    display_name = fields.Char(
        string='Timetable', compute='_compute_display_name', store=True
    )
    class_id = fields.Many2one(
        'school.class', string='Class', required=True, tracking=True
    )
    academic_year_id = fields.Many2one(
        'school.academic.year', string='Academic Year',
        related='class_id.academic_year_id', store=True
    )
    school_id = fields.Many2one(
        'school.branch', string='School',
        related='class_id.school_id', store=True
    )
    state = fields.Selection([
        ('draft', 'Draft'),
        ('active', 'Active'),
        ('archived', 'Archived'),
    ], string='Status', default='draft', tracking=True)
    slot_ids = fields.One2many(
        'school.timetable.slot', 'timetable_id', string='Slots'
    )
    slot_count = fields.Integer(
        string='Slots', compute='_compute_slot_count', store=True
    )
    timetable_html = fields.Html(
        string='Weekly Grid', compute='_compute_timetable_html', sanitize=False
    )
    notes = fields.Text(string='Notes')

    @api.depends('class_id', 'name')
    def _compute_display_name(self):
        for rec in self:
            class_name = rec.class_id.display_name or ''
            rec.display_name = f"{class_name} — {rec.name}" if class_name else (rec.name or '')

    @api.depends('slot_ids')
    def _compute_slot_count(self):
        for rec in self:
            rec.slot_count = len(rec.slot_ids)

    @api.constrains('class_id', 'state')
    def _check_one_active_per_class(self):
        for rec in self:
            if rec.state == 'active':
                conflict = self.search([
                    ('class_id', '=', rec.class_id.id),
                    ('state', '=', 'active'),
                    ('id', '!=', rec.id),
                ])
                if conflict:
                    raise ValidationError(_(
                        'Class %s already has an active timetable (%s).'
                    ) % (rec.class_id.display_name, conflict[0].name))

    @api.depends(
        'slot_ids', 'slot_ids.day_of_week', 'slot_ids.period_id',
        'slot_ids.subject_id', 'slot_ids.teacher_id', 'slot_ids.room',
    )
    def _compute_timetable_html(self):
        periods = self.env['school.period'].search(
            [('active', '=', True)], order='sequence'
        )
        for rec in self:
            idx = {(s.day_of_week, s.period_id.id): s for s in rec.slot_ids}

            html = ('<table class="table table-bordered table-sm text-center mb-0"'
                    ' style="font-size:0.85em;">')
            html += '<thead class="table-dark"><tr><th style="min-width:110px">Period</th>'
            for d in DAY_ORDER:
                html += f'<th>{DAY_LABELS[d]}</th>'
            html += '</tr></thead><tbody>'

            for p in periods:
                t_range = f'{_float_to_hhmm(p.time_start)} – {_float_to_hhmm(p.time_end)}'
                if p.is_break:
                    html += (
                        f'<tr class="table-secondary">'
                        f'<td colspan="6" class="fst-italic text-muted py-1">'
                        f'{p.name} &nbsp;·&nbsp; {t_range}'
                        f'</td></tr>'
                    )
                    continue
                html += (
                    f'<tr><td class="fw-semibold">{p.name}'
                    f'<br/><small class="fw-normal text-muted">{t_range}</small></td>'
                )
                for d in DAY_ORDER:
                    slot = idx.get((d, p.id))
                    if slot:
                        room = (f'<br/><small class="text-muted">{slot.room}</small>'
                                if slot.room else '')
                        html += (
                            f'<td style="background:#e8f4fd">'
                            f'<strong>{slot.subject_id.name}</strong>'
                            f'<br/><small>{slot.teacher_id.name}</small>'
                            f'{room}</td>'
                        )
                    else:
                        html += '<td class="text-muted">—</td>'
                html += '</tr>'

            if not periods:
                html += '<tr><td colspan="6" class="text-muted">No periods configured.</td></tr>'

            html += '</tbody></table>'
            rec.timetable_html = html

    def action_activate(self):
        self.write({'state': 'active'})

    def action_reset_draft(self):
        self.write({'state': 'draft'})

    def action_archive_timetable(self):
        self.write({'state': 'archived'})

    def action_print_timetable(self):
        return self.env.ref(
            'school_management.action_report_timetable'
        ).report_action(self)


class SchoolTimetableSlot(models.Model):
    _name = 'school.timetable.slot'
    _description = 'Timetable Slot'
    _order = 'day_of_week, time_start'

    timetable_id = fields.Many2one(
        'school.timetable', required=True, ondelete='cascade'
    )
    class_id = fields.Many2one(
        'school.class', related='timetable_id.class_id', store=True
    )
    academic_year_id = fields.Many2one(
        'school.academic.year',
        related='timetable_id.academic_year_id', store=True
    )

    day_of_week = fields.Selection(DAY_SELECTION, string='Day', required=True)
    period_id = fields.Many2one(
        'school.period', string='Period', required=True,
        domain=[('is_break', '=', False), ('active', '=', True)]
    )
    time_start = fields.Float(
        string='Start', related='period_id.time_start', store=True
    )
    time_end = fields.Float(
        string='End', related='period_id.time_end', store=True
    )

    subject_id = fields.Many2one('school.subject', string='Subject', required=True)
    teacher_id = fields.Many2one('school.teacher', string='Teacher', required=True)
    room = fields.Char(string='Room')

    _sql_constraints = [
        ('class_day_period_unique',
         'UNIQUE(timetable_id, day_of_week, period_id)',
         'This class already has a subject at this day and period.'),
    ]

    @api.constrains('teacher_id', 'day_of_week', 'period_id', 'academic_year_id')
    def _check_teacher_conflict(self):
        for slot in self:
            if not (slot.teacher_id and slot.day_of_week and slot.period_id):
                continue
            conflict = self.search([
                ('teacher_id', '=', slot.teacher_id.id),
                ('day_of_week', '=', slot.day_of_week),
                ('period_id', '=', slot.period_id.id),
                ('academic_year_id', '=', slot.academic_year_id.id),
                ('id', '!=', slot.id),
            ])
            if conflict:
                day = DAY_LABELS.get(slot.day_of_week, slot.day_of_week)
                raise ValidationError(_(
                    'Teacher %s is already assigned on %s - %s (Class: %s).'
                ) % (
                    slot.teacher_id.name, day, slot.period_id.name,
                    conflict[0].class_id.display_name,
                ))
