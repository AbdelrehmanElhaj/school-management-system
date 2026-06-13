# -*- coding: utf-8 -*-
from odoo import http, _
from odoo.http import request
from odoo.addons.portal.controllers.portal import CustomerPortal, pager as portal_pager


class SchoolPortal(CustomerPortal):

    def _prepare_home_portal_values(self, counters):
        values = super()._prepare_home_portal_values(counters)
        partner = request.env.user.partner_id

        guardian = request.env['school.guardian'].sudo().search(
            [('user_id', '=', request.env.uid)], limit=1
        )

        if 'student_count' in counters:
            values['student_count'] = len(guardian.student_ids) if guardian else 0
        if 'fee_count' in counters:
            values['fee_count'] = request.env['school.fee'].sudo().search_count(
                [('guardian_id', '=', guardian.id), ('state', '!=', 'cancelled')]
            ) if guardian else 0
        return values

    # ── My Children ──────────────────────────────────────────────────────────

    @http.route('/my/students', type='http', auth='user', website=True)
    def portal_my_students(self, **kw):
        guardian = request.env['school.guardian'].sudo().search(
            [('user_id', '=', request.env.uid)], limit=1
        )
        students = guardian.student_ids if guardian else []
        return request.render(
            'school_management.portal_my_students',
            {'students': students, 'guardian': guardian, 'page_name': 'students'}
        )

    @http.route('/my/students/<int:student_id>', type='http', auth='user', website=True)
    def portal_student_detail(self, student_id, **kw):
        guardian = request.env['school.guardian'].sudo().search(
            [('user_id', '=', request.env.uid)], limit=1
        )
        student = request.env['school.student'].sudo().browse(student_id)
        if not guardian or student.guardian_id != guardian:
            return request.redirect('/my/students')

        attendance = request.env['school.attendance'].sudo().search(
            [('student_id', '=', student_id)], order='date desc', limit=30
        )
        grades = request.env['school.grade'].sudo().search(
            [('student_id', '=', student_id)], order='exam_id desc'
        )
        fees = request.env['school.fee'].sudo().search(
            [('student_id', '=', student_id), ('state', '!=', 'cancelled')]
        )
        return request.render(
            'school_management.portal_student_detail',
            {
                'student': student,
                'attendance': attendance,
                'grades': grades,
                'fees': fees,
                'page_name': 'students',
            }
        )

    # ── My Fees ───────────────────────────────────────────────────────────────

    @http.route('/my/fees', type='http', auth='user', website=True)
    def portal_my_fees(self, **kw):
        guardian = request.env['school.guardian'].sudo().search(
            [('user_id', '=', request.env.uid)], limit=1
        )
        fees = request.env['school.fee'].sudo().search(
            [('guardian_id', '=', guardian.id), ('state', '!=', 'cancelled')]
        ) if guardian else []
        return request.render(
            'school_management.portal_my_fees',
            {'fees': fees, 'guardian': guardian, 'page_name': 'fees'}
        )

    # ── Announcements ─────────────────────────────────────────────────────────

    @http.route('/announcements', type='http', auth='public', website=True)
    def portal_announcements(self, **kw):
        from odoo import fields as odoo_fields
        today = odoo_fields.Date.today()
        announcements = request.env['school.announcement'].sudo().search([
            ('state', '=', 'published'),
            ('date_publish', '<=', today),
            '|', ('date_expire', '=', False), ('date_expire', '>=', today),
        ], order='date_publish desc')
        return request.render(
            'school_management.portal_announcements',
            {'announcements': announcements, 'page_name': 'announcements'}
        )

    @http.route('/announcements/<int:announcement_id>', type='http', auth='public', website=True)
    def portal_announcement_detail(self, announcement_id, **kw):
        announcement = request.env['school.announcement'].sudo().browse(announcement_id)
        if not announcement.exists() or announcement.state != 'published':
            return request.redirect('/announcements')
        return request.render(
            'school_management.portal_announcement_detail',
            {'announcement': announcement, 'page_name': 'announcements'}
        )
