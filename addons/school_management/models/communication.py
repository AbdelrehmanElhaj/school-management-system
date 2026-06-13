# -*- coding: utf-8 -*-
from odoo import models, fields, api, _
from odoo.exceptions import UserError


class SchoolAnnouncement(models.Model):
    _name = 'school.announcement'
    _description = 'School Announcement'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'date_publish desc'

    name = fields.Char(string='Title', required=True, tracking=True)
    body = fields.Html(string='Content', required=True, sanitize=True)
    date_publish = fields.Date(
        string='Publish Date', default=fields.Date.today, required=True
    )
    date_expire = fields.Date(string='Expiry Date')
    audience = fields.Selection([
        ('all', 'Everyone'),
        ('parents', 'Parents Only'),
        ('teachers', 'Teachers Only'),
        ('students', 'Students Only'),
    ], string='Audience', default='all', required=True, tracking=True)
    class_ids = fields.Many2many(
        'school.class', string='Target Classes',
        help='Leave empty to target all classes'
    )
    state = fields.Selection([
        ('draft', 'Draft'),
        ('published', 'Published'),
        ('archived', 'Archived'),
    ], default='draft', tracking=True)
    send_email = fields.Boolean(string='Notify by Email', default=False)
    email_sent = fields.Boolean(string='Email Sent', readonly=True, copy=False)
    recipient_count = fields.Integer(
        string='Recipients', compute='_compute_recipient_count'
    )
    attachment_ids = fields.Many2many('ir.attachment', string='Attachments')

    # ── State transitions ─────────────────────────────────────────────────────
    def action_publish(self):
        for rec in self:
            rec.state = 'published'
            if rec.send_email and not rec.email_sent:
                rec._send_email_blast()

    def action_archive_announcement(self):
        self.write({'state': 'archived'})

    def action_reset_draft(self):
        self.write({'state': 'draft'})

    # ── Recipients ────────────────────────────────────────────────────────────
    def _get_recipient_emails(self):
        emails = set()
        if self.audience in ('all', 'parents'):
            domain = [('email', '!=', False)]
            if self.class_ids:
                students = self.env['school.student'].search([
                    ('class_id', 'in', self.class_ids.ids),
                    ('status', '=', 'active'),
                ])
                guardians = students.mapped('guardian_id').filtered('email')
            else:
                guardians = self.env['school.guardian'].search(domain)
            emails.update(g.email for g in guardians if g.email)

        if self.audience in ('all', 'teachers'):
            teachers = self.env['school.teacher'].search([
                ('email', '!=', False), ('status', '=', 'active'),
            ])
            emails.update(t.email for t in teachers if t.email)

        return list(emails)

    @api.depends('audience', 'class_ids')
    def _compute_recipient_count(self):
        for rec in self:
            rec.recipient_count = len(rec._get_recipient_emails())

    # ── Email blast ───────────────────────────────────────────────────────────
    def _send_email_blast(self):
        emails = self._get_recipient_emails()
        if not emails:
            raise UserError(_('No email addresses found for the selected audience.'))
        mail = self.env['mail.mail'].create({
            'subject': self.name,
            'body_html': self.body or '',
            'email_to': ','.join(emails),
            'auto_delete': True,
        })
        mail.send()
        self.email_sent = True
        self.message_post(
            body=_('Announcement emailed to %d recipients.') % len(emails)
        )

    def action_send_email_now(self):
        for rec in self:
            rec._send_email_blast()
