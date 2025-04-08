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

from odoo import models, fields, api
from datetime import date, datetime, time


class OpDepartment(models.Model):
    _name = "op.department"
    _description = "OpenEduCat Department"
    _order = 'id desc'

    name = fields.Char('Name', required=True)
    # code = fields.Char('Code', required=True)
    code = fields.Char(string="Department ID No.", required=True, copy=False, readonly=False, default="New")
    category_id = fields.Many2one('op.category', string="Category", required=1)
    type = fields.Selection([("regular", "Regular"), ("crash", "Crash")], string="Type")
    parent_id = fields.Many2one('op.department', 'Parent Department')

    # @api.model_create_multi
    # def create(self, vals):
    #     department = super(OpDepartment, self).create(vals)
    #     self.env.user.write({'department_ids': [(4, department.id)]})
    #     return department

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

        return super(OpDepartment, self).create(vals)

    def act_create_sub_course(self):
        return {
            'type': 'ir.actions.act_window',
            'view_mode': 'form',
            'res_model': 'op.course',
            'target': 'new',
            'context': {'default_department_id': self.id},

        }
