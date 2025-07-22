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
from odoo.exceptions import UserError


class OpSubject(models.Model):
    _name = "op.subject"
    _inherit = "mail.thread"
    _description = "Subject"
    _order = 'id desc'

    name = fields.Char('Name', size=128, required=True)
    code = fields.Char('Code', size=256, required=True)
    # grade_weightage = fields.Float('Grade Weightage')
    type = fields.Selection(
        [('theory', 'Theory'), ('practical', 'Practical'),
         ('both', 'Both'), ('other', 'Other')],
        'Type', default="theory", required=True)
    standard_hour = fields.Float(string="Standard Hour")

    subject_type = fields.Selection(
        [('compulsory', 'Compulsory'), ('elective', 'Elective')],
        'Subject Type', default="compulsory", required=True)
    department_id = fields.Many2one(
        'op.department', 'Department',
        default=lambda self:
        self.env.user.dept_id and self.env.user.dept_id.id or False)
    active = fields.Boolean(default=True)
    group = fields.Many2one('op.group', string="Group")
    mode_of_study = fields.Selection([('online', 'Online'), ('offline', 'Offline'), ('nil', 'Nil')],
                                     string="Mode of Study", default="offline")
    course_id = fields.Many2one('op.course', string="Course", required=1)
    opening_hour = fields.Float(string="Opening Hours", readonly=1)
    description = fields.Text(string="Description")
    active_add_on = fields.Boolean(string="Active Add On")
    state = fields.Selection([('draft','Draft'), ('done','Done')], string="Status", default="draft")

    def act_add_opening_balance(self):
        return {'type': 'ir.actions.act_window',
                'name': _('Add On Hours'),
                'res_model': 'add.on.hours',
                'target': 'new',
                'view_mode': 'form',
                'view_type': 'form',
                'context': {'default_record_id': self.id}, }

    def act_add_to_course(self):
        for i in self:
            if i.course_id:
                i.course_id.subject_ids = [(4, i.id)]
                i.state = 'done'

    def revert(self):
        self.state = 'draft'

    _sql_constraints = [
        ('unique_subject_code',
         'unique(code)', 'Code should be unique per subject!'),
    ]

    @api.model
    def get_import_templates(self):
        return [{
            'label': _('Import Template for Subjects'),
            'template': '/openeducat_core/static/xls/op_subject.xls'
        }]


class AddOnStandardHours(models.TransientModel):
   _name = 'add.on.hours'
   _description = "Add On Hours Wizard"

   record_id = fields.Many2one('op.subject', string="Record")
   add_on_time = fields.Float(string="Add On Time", required=True)
   description = fields.Text(string="Description", required=True)

   def act_confirm(self):
       if self.add_on_time == 0:
           raise UserError(_("Please add Time"))
       else:
           self.record_id.opening_hour = self.add_on_time
           self.record_id.description = self.description
           self.record_id.active_add_on = True

