# -*- coding: utf-8 -*-
from odoo import models, fields, api, _
from odoo.exceptions import UserError


class QrSession(models.Model):
    _name = 'school.qr.session'
    _description = 'QR Attendance Session'
    _order = 'date desc, id desc'
    _rec_name = 'name'

    name = fields.Char(string='Session Name', required=True)
    class_id = fields.Many2one('school.class', string='Class', required=True)
    teacher_id = fields.Many2one('school.teacher', string='Teacher')
    date = fields.Date(string='Date', required=True, default=fields.Date.today)
    state = fields.Selection([
        ('open', 'Open'),
        ('closed', 'Closed'),
    ], string='Status', default='open', required=True)

    attendance_ids = fields.One2many(
        'school.attendance', 'qr_session_id', string='Attendance Records'
    )
    scan_count = fields.Integer(
        string='Students Scanned', compute='_compute_scan_count', store=True
    )
    kiosk_url = fields.Char(string='Kiosk URL', compute='_compute_kiosk_url')

    @api.depends('attendance_ids')
    def _compute_scan_count(self):
        for rec in self:
            rec.scan_count = len(rec.attendance_ids)

    def _compute_kiosk_url(self):
        base = self.env['ir.config_parameter'].sudo().get_param('web.base.url')
        for rec in self:
            rec.kiosk_url = f"{base}/school/qr/scanner?session_id={rec.id}"

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if 'name' not in vals or vals.get('name') == _('New'):
                class_rec = self.env['school.class'].browse(vals.get('class_id'))
                date_str = vals.get('date', str(fields.Date.today()))
                vals['name'] = f"حضور - {class_rec.name} - {date_str}"
        return super().create(vals_list)

    def action_close(self):
        return self.write({'state': 'closed'})

    def action_reopen(self):
        self.write({'state': 'open'})

    def action_open_kiosk(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_url',
            'url': self.kiosk_url,
            'target': 'new',
        }
