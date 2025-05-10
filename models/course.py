# -*- coding: utf-8 -*-
###############################################################################
#
#    OpenEduCat Inc
#    Copyright (C) 2009-TODAY OpenEduCat Inc(<https://www.openeducat.org>).
#
#    This program is free software: you can redistribute it and/or modify
#    it under the terms of the GNU Lesser General Public License as
#    published by the Free Software Foundation, either version 3 of the
#    License, or (at your option) any later version.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU Lesser General Public License for more details.
#
#    You should have received a copy of the GNU Lesser General Public License
#    along with this program.  If not, see <http://www.gnu.org/licenses/>.
#
###############################################################################

from odoo import models, fields, api, _
from odoo.exceptions import ValidationError
from datetime import date, datetime, time


class OpCourse(models.Model):
    _name = "op.course"
    _inherit = "mail.thread"
    _description = "OpenEduCat Course"
    _order = 'id desc'

    name = fields.Char('Name', required=True)
    code = fields.Char(string="Course ID No.", required=True, copy=False, readonly=False, default="New")
    parent_id = fields.Many2one('op.course', 'Parent Course')
    evaluation_type = fields.Selection(
        [('normal', 'Normal'), ('GPA', 'GPA'),
         ('CWA', 'CWA'), ('CCE', 'CCE')],
        'Evaluation Type', default="normal",)
    subject_ids = fields.Many2many('op.subject', string='Subject(s)')
    max_unit_load = fields.Float("Maximum No.of Students")
    min_unit_load = fields.Float("Minimum No.of Students")
    department_id = fields.Many2one(
        'op.department', 'Department',
        default=lambda self:
        self.env.user.dept_id and self.env.user.dept_id.id or False)
    active = fields.Boolean(default=True)
    type = fields.Selection([('regular', 'Regular'), ('crash', 'Crash')], string='Type', required=1)
    # branch_id = fields.Many2one('logic.branches', string="Branch")
    course_type = fields.Selection(
        [('indian', 'Indian'), ('international', 'International'), ('crash', 'Crash'), ('repeaters', 'Repeaters'),
         ('nil', 'Nil')], string="Type")
    academic_head_id = fields.Many2one('res.users', string="Academic Head")
    board_registration = fields.Boolean(string="Board Registration")
    tayyap_course = fields.Boolean(string="Tayyap Course")

    # related_product_id = fields.Many2one('product.product', string="Related Product")
    # course_fee = fields.Float(string="Course Fee", related="related_product_id.list_price")
    # product_added = fields.Boolean(string="Product Added")

    # _sql_constraints = [
    #     ('unique_course_code',
    #      'unique(code)', 'Code should be unique per course!')]

    @api.constrains('parent_id')
    def _check_parent_id_recursion(self):
        if not self._check_recursion():
            raise ValidationError(_('You cannot create recursive Course.'))
        return True

    @api.model
    def get_import_templates(self):
        return [{
            'label': _('Import Template for Courses'),
            'template': '/openeducat_core/static/xls/op_course.xls'
        }]

    @api.model
    def create(self, vals):
        # Get the current year
        current_year = datetime.today().year

        # Find the latest code in the same year
        last_course = self.search([('code', 'like', f'{current_year}/%')], order='id desc', limit=1)

        if last_course and last_course.code:
            # Extract the last number and increment
            last_number = int(last_course.code.split('/')[1])  # Get "01" as integer
            new_number = str(last_number + 1).zfill(2)  # Ensure 2-digit format
        else:
            new_number = "01"  # Start from 01 if no records exist

        # Generate new course code
        vals['code'] = f"{current_year}/{new_number}"

        return super(OpCourse, self).create(vals)

    def act_create_product(self):
        return {'type': 'ir.actions.act_window',
                'name': _('Details'),
                'res_model': 'logic.product.details',
                'target': 'new',
                'view_mode': 'form',
                'view_type': 'form',
                'context': {'default_name': self.name,
                            'default_course_id': self.id
                            }, }


class ProductDetails(models.TransientModel):
    _name = 'logic.product.details'

    name = fields.Char(string="Name")
    price = fields.Float(string="Price")
    course_id = fields.Many2one('op.course')

    def action_create_product(self):
        product = self.env['product.product'].sudo().create({
            'name': self.name,
            'list_price': self.price,
            'detailed_type': 'service',

        })
        # self.course_id.related_product_id = product.id
        # self.course_id.product_added = True
