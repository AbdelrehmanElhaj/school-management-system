# -*- coding: utf-8 -*-
from odoo import models, fields, api, _
from odoo.exceptions import UserError


class SchoolCommunicationWizard(models.TransientModel):
    _name = 'school.communication.wizard'
    _description = 'Bulk Parent Communication'

    subject = fields.Char(string='Subject', required=True)
    body = fields.Html(string='Message', required=True)
    class_ids = fields.Many2many('school.class', string='Target Classes')
    student_ids = fields.Many2many('school.student', string='Additional Students')
    recipient_preview = fields.Text(
        string='Recipients Preview', compute='_compute_preview', readonly=True
    )
    recipient_count = fields.Integer(
        string='Recipient Count', compute='_compute_preview'
    )

    @api.depends('class_ids', 'student_ids')
    def _compute_preview(self):
        for rec in self:
            emails = rec._get_guardian_emails()
            rec.recipient_count = len(emails)
            rec.recipient_preview = '\n'.join(sorted(emails)) if emails else _('No recipients found.')

    def _get_guardian_emails(self):
        students = self.student_ids
        if self.class_ids:
            class_students = self.env['school.student'].search([
                ('class_id', 'in', self.class_ids.ids),
                ('status', '=', 'active'),
            ])
            students = students | class_students
        guardians = students.mapped('guardian_id').filtered('email')
        return list({g.email for g in guardians if g.email})

    def action_send(self):
        self.ensure_one()
        emails = self._get_guardian_emails()
        if not emails:
            raise UserError(_('No guardian emails found for the selected students/classes.'))

        mail = self.env['mail.mail'].create({
            'subject': self.subject,
            'body_html': self.body or '',
            'email_to': ','.join(emails),
            'auto_delete': True,
        })
        mail.send()

        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'message': _('Message sent to %d guardians.') % len(emails),
                'type': 'success',
                'sticky': False,
            }
        }
