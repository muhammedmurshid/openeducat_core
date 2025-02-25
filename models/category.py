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
from datetime import date, datetime, time


class OpCategory(models.Model):
    _name = "op.category"
    _description = "OpenEduCat Category"
    _order = 'id desc'

    name = fields.Char('Name', size=256, required=True)
    # code = fields.Char('Code', size=16, required=True)
    type = fields.Selection([("regular", "Regular"), ("crash", "Crash")], string="Type")
    code = fields.Char(string="Category ID No.", required=True, copy=False, readonly=False, default="New")


    _sql_constraints = [
        ('unique_category_code',
         'unique(code)', 'Code should be unique per category!')]

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

        return super(OpCategory, self).create(vals)
