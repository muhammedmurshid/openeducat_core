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
from datetime import date,datetime, timedelta
import re


class OpBatch(models.Model):
    _name = "op.batch"
    _inherit = "mail.thread"
    _description = "OpenEduCat Batch"
    _order = 'id desc'

    code = fields.Char('Batch ID No.', copy=False, readonly=False, default="New")
    name = fields.Char('Name', required=True)
    start_date = fields.Date(
        'Start Date', required=True, default=fields.Date.today(), tracking=1)
    end_date = fields.Date('End Date', store=1, required=1, tracking=1)
    active = fields.Boolean(default=True)
    department_id = fields.Many2one('op.department', string="Department", required=1)
    state = fields.Selection(
        [('draft', 'Draft'), ('batch_approval', 'Batch Approval'), ('marketing', 'Marketing'), ('accounts', 'Accounts'), ('completed', 'Completed'), ('up_coming', 'Up Coming')],
        string="Status", default='draft', tracking=True)
    remaining_days = fields.Integer(string="Days to End Batch", compute="_compute_remaining_days", store=1)
    # branch_id = fields.Many2one('op.branch', string="Branch")
    admission_fee = fields.Float(string="Admission Fee", compute="_compute_adm_total_fee", store=1, tracking=1)
    adm_tax = fields.Float(string="Tax")
    adm_exc_fee = fields.Float(string="Admission Fee (Exc Fee)")
    adm_inc_fee = fields.Float(string="Admission Fee (Inc Fee)")
    course_fee = fields.Integer(string="Course Fee")
    student_ids = fields.One2many('logic.student.list', 'batch_id', )
    initiated_id = fields.Many2one('res.users', string="Initiated By", required=1)
    class_type = fields.Selection([('online', 'Online'), ('offline', 'Offline')], string="Class Type")
    fee_type = fields.Selection([('lump_sum_fee', 'Lump Sum Fee'), ('loan', 'Loan'), ('installment', 'Installment')],
                                string="Fee Type", default="lump_sum_fee", required=1)
    lump_fee_excluding_tax = fields.Float(string="Excluding Tax")
    tax = fields.Float(string="Tax")
    lump_fee_including_tax = fields.Float(string="Including Tax")
    currency_id = fields.Many2one(
        'res.currency', string='Currency',
        default=lambda self: self.env.user.company_id.currency_id.id)
    academic_year = fields.Selection([('2020-2021','2020-2021'), ('2021-2022','2021-2022'), ('2022-2023','2022-2023'), ('2023-2024','2023-2024'), ('2024-2025','2024-2025'), ('2025-2026','2025-2026'), ('2026-2027','2026-2027')], string="Academic Year", required=1)
    total_lump_sum_fee = fields.Float(string="Total Fee", compute='_compute_total_lump_sum_fee', store=1, tracking=1)
    batch_type = fields.Selection(
        [('present_batch', 'Running Batch'), ('future_batch', 'Future Batch'), ('ended_batch', 'Ended Batch') ],
        string="Type", default='present_batch', tracking=True)
    #lump sum plan offer
    term = fields.Char(string="Term")
    amount_exc_lump = fields.Float(string="Amount(Excluding Tax)")
    tax_amount_lump = fields.Float(string="Tax Amount")
    amount_inc_lump = fields.Float(string="Amount(Including Tax)", compute='_compute_amount_inc_lump', store=1)
    payment_date_lump = fields.Date(string="Payment Date")
    difference_in_fee_lump = fields.Float(string="Difference in fee", compute='_compute_amount_inc_lump', store=1)
    installment_ids = fields.One2many('payment.installment.type', 'installment_id')
    max_no_of_students = fields.Integer(string="Max no.of Students")
    compo_ids = fields.One2many('payment.group.compo', 'compo_id')

    @api.model
    def create(self, vals):
        current_year = datetime.today().year
        max_number = 0

        # Search all records for the current year
        batches = self.search([('code', 'like', f'{current_year}/%')])

        for batch in batches:
            if batch.code:
                match = re.match(rf"{current_year}/(\d+)", batch.code)
                if match:
                    number = int(match.group(1))
                    if number > max_number:
                        max_number = number

        # Increment the highest number found
        new_number = str(max_number + 1).zfill(2)

        # Assign the new code
        vals['code'] = f"{current_year}/{new_number}"

        return super(OpBatch, self).create(vals)

    active_badge = fields.Char(string="Status", compute="_compute_active_badge")

    @api.depends('active')
    def _compute_active_badge(self):
        for record in self:
            record.active_badge = "Active" if record.active else ""

    @api.depends('student_ids', 'student_ids.state')
    def _compute_total_students(self):
        for record in self:
            record.total_no_of_students = len(record.student_ids.filtered(lambda s: s.state != 'stoped'))

    total_no_of_students = fields.Integer(string="No. of Students", compute="_compute_total_students", store=True)

    @api.depends('adm_exc_fee','adm_inc_fee')
    def _compute_adm_total_fee(self):
        for i in self:
            if i.adm_exc_fee != 0:
                i.adm_tax = i.adm_exc_fee * 18 /100
                i.adm_inc_fee = i.adm_exc_fee + i.adm_tax
            if i.adm_inc_fee != 0:
                i.admission_fee = i.adm_inc_fee


    @api.depends('amount_exc_lump','tax_amount_lump','amount_inc_lump','total_lump_sum_fee')
    def _compute_amount_inc_lump(self):
        for i in self:
            if i.tax_amount_lump != 0:
                i.amount_inc_lump = i.amount_exc_lump + i.tax_amount_lump
            if i.total_lump_sum_fee != 0 and i.amount_inc_lump !=0:
                i.difference_in_fee_lump = i.total_lump_sum_fee - i.amount_inc_lump

    @api.depends('lump_fee_including_tax','lump_fee_excluding_tax')
    def _compute_total_lump_sum_fee(self):
        for i in self:
            if i.lump_fee_excluding_tax != 0:
                i.tax = i.lump_fee_excluding_tax * 18 / 100
            i.lump_fee_including_tax = i.lump_fee_excluding_tax + i.tax
            i.total_lump_sum_fee = i.lump_fee_excluding_tax + i.tax

    inst_amount_exc = fields.Float(string="Amount (Exc Tax)", compute="_compute_total_amount_installment", store=1)
    inst_amount_tax = fields.Float(string="Tax", compute="_compute_total_amount_installment", store=1)
    inst_amount_inc = fields.Float(string="Amount (Inc Tax)", compute="_compute_total_amount_installment", store=1,)
    total_installment_fee = fields.Float(string="Total Fee", compute="_compute_total_installment_fee", store=1, readonly=0, tracking=1)
    compo_amount_exc = fields.Float(string="Amount (Exc Tax)", compute="_compute_total_amount_compo", store=1)
    compo_amount_tax = fields.Float(string="Tax", compute="_compute_total_amount_compo", store=1)
    compo_amount_inc = fields.Float(string="Amount (Inc Tax)", compute="_compute_total_amount_compo", store=1, )
    compo_total_fee = fields.Float(string="Total Fee", compute="_compute_total_compo_fee", store=1,
                                         readonly=0)

    # @api.onchange('inst_amount_exc','inst_amount_tax')
    # def _onchange_total_installment_amount(self):
    #     self.inst_amount_inc = self.inst_amount_exc + self.inst_amount_tax

    @api.depends('compo_ids', 'compo_ids.amount_exc_compo', 'compo_ids.tax_amount_compo',
                 'compo_ids.amount_inc_compo')
    def _compute_total_amount_compo(self):
        for i in self:
            if i.compo_ids:
                total = 0
                total_inc = 0
                for amt in self.compo_ids:
                    total += amt.amount_exc_compo
                    total_inc += amt.amount_inc_compo
                i.compo_amount_exc = total
                if total != 0:
                    i.compo_amount_tax = total * 18 / 100
                i.compo_amount_inc = total_inc
            else:
                i.compo_amount_exc = 0
                i.compo_amount_inc = 0

    @api.depends('inst_amount_exc','inst_amount_tax','inst_amount_inc')
    def _compute_total_installment_fee(self):
        for rec in self:
            if rec.inst_amount_inc != 0:
                rec.total_installment_fee = rec.inst_amount_inc

    @api.depends('compo_amount_exc', 'compo_amount_tax', 'compo_amount_inc')
    def _compute_total_compo_fee(self):
        for rec in self:
            if rec.compo_amount_inc != 0:
                rec.compo_total_fee = rec.compo_amount_inc

    @api.depends('installment_ids','installment_ids.amount_exc_installment','installment_ids.tax_amount','installment_ids.amount_inc_installment')
    def _compute_total_amount_installment(self):
        for i in self:
            if i.installment_ids:
                total = 0
                total_inc = 0
                for amt in self.installment_ids:
                    total += amt.amount_exc_installment
                    total_inc += amt.amount_inc_installment
                i.inst_amount_exc = total
                if total !=0:
                    i.inst_amount_tax = total * 18 /100
                i.inst_amount_inc = total_inc
            else:
                i.inst_amount_exc = 0
                i.inst_amount_inc = 0


    def act_confirm_batch(self):
        self.state = 'batch_approval'
        print('hi')

    _sql_constraints = [
        ('unique_batch_code',
         'unique(code)', 'Code should be unique per batch!')]

    total_duration = fields.Integer(string="Duration", required=1)

    @api.onchange('start_date', 'total_duration')
    def _onchange_end_date(self):
        for record in self:
            if record.start_date and record.total_duration:
                record.end_date = record.start_date + timedelta(days=record.total_duration - 1)
            else:
                record.end_date = False

    days_to_batch_start = fields.Integer(string="Days to Strat Batch", compute="_compute_remaining_days", store=1)

    @api.depends('start_date', 'end_date','total_duration')
    def _compute_remaining_days(self):
        for record in self:
            if record.start_date:
                today = date.today()
                if record.start_date <= today:
                    elapsed_days = (today - record.start_date).days
                    print(elapsed_days, 'elapsed')
                    record.days_to_batch_start = elapsed_days

                else:
                    record.days_to_batch_start = 0
                    if record.end_date:
                        print('end')
                        end_date = record.end_date
                        print(end_date, 'date end', today)
                        # Compute remaining days
                        remaining_days = (record.end_date - today).days
                        print(remaining_days, 'days')
                        # record.remaining_days = remaining_days
                        # Ensure no negative remaining days
                        record.remaining_days = max(remaining_days, 0)
                    else:
                        record.remaining_days = 0
                    print('future batch')

                    # record.remaining_days = 0
    def action_cron_batch_type(self):
        today = date.today()
        batches = self.env['op.batch'].search([])  # fetch all batches

        for record in batches:
            if record.start_date and record.end_date:
                if record.start_date < today < record.end_date:
                    record.batch_type = 'present_batch'
                    print('running_batch')
                elif today < record.start_date:
                    record.batch_type = 'future_batch'
                    print('future_batch')
                elif today > record.end_date:
                    record.batch_type = 'ended_batch'
                    print('ended_batch')

    @api.constrains('start_date', 'end_date')
    def check_dates(self):
        for record in self:
            if record.start_date and record.end_date:
                start_date = fields.Date.from_string(record.start_date)
                end_date = fields.Date.from_string(record.end_date)
                if start_date > end_date:
                    raise ValidationError(
                        _("End Date cannot be set before Start Date."))

    @api.onchange('department_id')
    def _onchange_branch(self):
        if self.department_id:
            print(f"department_id ID: {self.department_id.id}")
            domain = [('department_id', '=', self.department_id.id)]
            print(f"Domain applied: {domain}")
            return {
                'domain': {
                    'course_id': domain,
                }
            }
        else:
            print("No branch selected")
            return {
                'domain': {
                    'course_id': [],
                }
            }
    course_id = fields.Many2one('op.course', 'Sub Course', domain="[('department_id', '=', department_id)]", required=1)

    @api.model
    def name_search(self, name, args=None, operator='ilike', limit=100):
        if self.env.context.get('get_parent_batch', False):
            lst = []
            lst.append(self.env.context.get('course_id'))
            courses = self.env['op.course'].browse(lst)
            while courses.parent_id:
                lst.append(courses.parent_id.id)
                courses = courses.parent_id
            batches = self.env['op.batch'].search([('course_id', 'in', lst)])
            return batches.name_get()
        return super(OpBatch, self).name_search(
            name, args, operator=operator, limit=limit)

    @api.model
    def get_import_templates(self):
        return [{
            'label': _('Import Template for Batch'),
            'template': '/openeducat_core/static/xls/op_batch.xls'
        }]

    def action_done_batch(self):
        self.state = 'completed'

    def allocate_students(self):
        new_students = self.env['op.student'].search([('batch_id', '=', self.id),('state', '!=', 'stoped')])

        for record in self:
            existing_students = record.student_ids.mapped('student_id')  # Get existing student_ids

            # Add students without duplicates
            for student in new_students:
                if student.id not in existing_students:  # Check if the student is already in the One2many field
                    print(student.name, 'student')
                    student.state = 'batch_allocated'
                    record.student_ids = [(0, 0, {'student_id': student.id, 'student_name': student.id,
                                                  'mobile': student.mobile, 'date_of_admission': student.admission_date})]


class StudentList(models.Model):
    _name = 'logic.student.list'

    student_id = fields.Integer(string="ID")
    student_name = fields.Many2one('op.student', string="Name")
    date_of_admission = fields.Date(string="Admission Date")
    admission_fee = fields.Integer(string="Admission Fee")
    course_fee = fields.Integer(string="Course Fee")
    total_paid = fields.Integer(string="Total Paid", compute="_compute_total_paid_amount", store=1)
    batch_id = fields.Many2one('op.batch', ondelete="cascade")
    mobile = fields.Char(string="Mobile")
    state = fields.Selection([('confirm', 'Confirm'), ('batch_allocated', 'Batch Allocated'),
                              ('stoped', 'Droped')],
                             string="Status", default="confirm",related='student_name.state')

    # @api.depends('student_name')
    # def _compute_student_status(self):
    #     for i in self:
    #         if i.student_name:
    #             print('workingggd')
    #             i.status = i.student_name.state

    @api.depends('course_fee', 'admission_fee')
    def _compute_total_paid_amount(self):
        for rec in self:
            rec.total_paid = rec.course_fee + rec.admission_fee

class InstallmentPayment(models.Model):
    _name = 'payment.installment.type'

    term = fields.Char(string="Term")
    amount_exc_installment = fields.Float(string="Amount(Excluding Tax)")
    tax_amount = fields.Float(string="Tax Amount")
    amount_inc_installment = fields.Float(string="Amount(Including Tax)", compute='_compute_amount_inc_installment', store=1)
    payment_date = fields.Date(string="Payment Date")
    installment_id = fields.Many2one('op.batch', string="Installment")
    currency_id = fields.Many2one(
        'res.currency', string='Currency',
        default=lambda self: self.env.user.company_id.currency_id.id)

    @api.depends('amount_exc_installment','tax_amount')
    def _compute_amount_inc_installment(self):
        for i in self:
            if i.amount_exc_installment != 0:
                i.tax_amount = i.amount_exc_installment * 18 / 100
            if i.tax_amount != 0:
                i.amount_inc_installment = i.amount_exc_installment + i.tax_amount

class GroupCompoPayment(models.Model):
    _name = 'payment.group.compo'

    term = fields.Char(string="Term")
    amount_exc_compo = fields.Float(string="Amount(Excluding Tax)")
    tax_amount_compo = fields.Float(string="Tax Amount")
    amount_inc_compo = fields.Float(string="Amount(Including Tax)", compute='_compute_amount_inc_compo', store=1)
    compo_id = fields.Many2one('op.batch', string="Compo")

    @api.depends('amount_exc_compo', 'tax_amount_compo')
    def _compute_amount_inc_compo(self):
        for i in self:
            if i.amount_exc_compo != 0:
                i.tax_amount_compo = i.amount_exc_compo * 18 / 100
            if i.tax_amount_compo != 0:
                i.amount_inc_compo = i.amount_exc_compo + i.tax_amount_compo