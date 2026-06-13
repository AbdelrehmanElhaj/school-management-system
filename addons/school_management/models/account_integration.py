# -*- coding: utf-8 -*-
from odoo import models, fields, api, _
from odoo.exceptions import UserError


class FeeAccountIntegration(models.Model):
    """Extend school.fee to support Odoo account.move invoice generation."""
    _inherit = 'school.fee'

    invoice_id = fields.Many2one(
        'account.move', string='Invoice', readonly=True, copy=False,
        domain=[('move_type', '=', 'out_invoice')]
    )
    invoice_state = fields.Selection(
        related='invoice_id.state', string='Invoice Status', readonly=True
    )
    invoice_amount_residual = fields.Monetary(
        related='invoice_id.amount_residual',
        string='Invoice Balance', readonly=True,
        currency_field='currency_id'
    )

    def action_create_invoice(self):
        """Generate an Odoo customer invoice from this fee record."""
        for rec in self:
            if rec.invoice_id:
                raise UserError(
                    _('An invoice already exists for this fee: %s') % rec.invoice_id.name
                )
            if rec.state not in ('due', 'partial', 'overdue'):
                raise UserError(
                    _('Invoice can only be created for due or overdue fees.')
                )

            # Find or create partner from guardian
            partner = None
            if rec.guardian_id and rec.guardian_id.email:
                partner = self.env['res.partner'].search(
                    [('email', '=', rec.guardian_id.email)], limit=1
                )
            if not partner and rec.guardian_id:
                partner = self.env['res.partner'].create({
                    'name': rec.guardian_id.name,
                    'email': rec.guardian_id.email or '',
                    'phone': rec.guardian_id.phone or '',
                    'mobile': rec.guardian_id.mobile or '',
                    'customer_rank': 1,
                })

            if not partner:
                raise UserError(
                    _('Cannot create invoice: no guardian or partner found for student %s.')
                    % rec.student_id.name
                )

            # Find income account (use first available or company default)
            account = self._get_income_account()

            invoice = self.env['account.move'].create({
                'move_type': 'out_invoice',
                'partner_id': partner.id,
                'invoice_date': rec.invoice_date or fields.Date.today(),
                'invoice_date_due': rec.due_date,
                'currency_id': rec.currency_id.id,
                'ref': rec.fee_code,
                'narration': _('Fee for student: %s | %s') % (
                    rec.student_id.name, rec.fee_type_id.name
                ),
                'invoice_line_ids': [(0, 0, {
                    'name': '%s - %s (%s)' % (
                        rec.fee_type_id.name,
                        rec.student_id.name,
                        rec.term or ''
                    ),
                    'quantity': 1.0,
                    'price_unit': rec.amount,
                    'account_id': account.id,
                })],
            })
            rec.invoice_id = invoice

        # Open the invoice
        if len(self) == 1:
            return {
                'type': 'ir.actions.act_window',
                'name': _('Invoice'),
                'res_model': 'account.move',
                'res_id': self.invoice_id.id,
                'view_mode': 'form',
            }
        return True

    def action_view_invoice(self):
        return {
            'type': 'ir.actions.act_window',
            'name': _('Invoice'),
            'res_model': 'account.move',
            'res_id': self.invoice_id.id,
            'view_mode': 'form',
        }

    def _get_income_account(self):
        """Return a suitable income account for the fee invoice line."""
        company = self.env.company
        # Try to find an income account from the chart of accounts
        account = self.env['account.account'].search([
            ('account_type', '=', 'income'),
            ('company_id', '=', company.id),
            ('deprecated', '=', False),
        ], limit=1)
        if not account:
            # Fallback: any account marked as income_other
            account = self.env['account.account'].search([
                ('account_type', '=', 'income_other'),
                ('company_id', '=', company.id),
                ('deprecated', '=', False),
            ], limit=1)
        if not account:
            raise UserError(
                _('No income account found. Please configure your Chart of Accounts.')
            )
        return account
