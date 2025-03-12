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
from os import unlink

from odoo import models, fields, api, _, tools, exceptions
from odoo.exceptions import ValidationError, UserError
from num2words import num2words
from datetime import date,datetime
import re

from odoo.tools.populate import compute


class OpStudentCourse(models.Model):
    _name = "op.student.course"
    _description = "Student Course Details"
    _inherit = "mail.thread"
    _rec_name = 'student_id'

    student_id = fields.Many2one('op.student', 'Student',
                                 ondelete="cascade", tracking=True)
    course_id = fields.Many2one('op.course', 'Course', required=True, tracking=True)
    batch_id = fields.Many2one('op.batch', 'Batch', required=True, tracking=True)
    roll_number = fields.Char('Roll Number', tracking=True)
    subject_ids = fields.Many2many('op.subject', string='Subjects')
    academic_years_id = fields.Many2one('op.academic.year', 'Academic Year')
    academic_term_id = fields.Many2one('op.academic.term', 'Terms')
    state = fields.Selection([('running', 'Running'),
                              ('finished', 'Finished')],
                             string="Status", default="running")
    currency_id = fields.Many2one(
        'res.currency',
        string="Currency",
        default=lambda self: self.env.company.currency_id.id,
    )

    _sql_constraints = [
        ('unique_name_roll_number_id',
         'unique(roll_number,course_id,batch_id,student_id)',
         'Roll Number & Student must be unique per Batch!'),
        ('unique_name_roll_number_course_id',
         'unique(roll_number,course_id,batch_id)',
         'Roll Number must be unique per Batch!'),
        ('unique_name_roll_number_student_id',
         'unique(student_id,course_id,batch_id)',
         'Student must be unique per Batch!'),
    ]

    @api.model
    def get_import_templates(self):
        return [{
            'label': _('Import Template for Student Course Details'),
            'template': '/openeducat_core/static/xls/op_student_course.xls'
        }]


class OpStudent(models.Model):
    _name = "op.student"
    _description = "Student"
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _inherits = {"res.partner": "partner_id"}
    _order = 'id desc'

    # first_name = fields.Char('First Name', translate=True)
    # middle_name = fields.Char('Middle Name', translate=True)
    # last_name = fields.Char('Last Name', translate=True)
    birth_date = fields.Date('Birth Date')
    blood_group = fields.Selection([
        ('A+', 'A+ve'),
        ('B+', 'B+ve'),
        ('O+', 'O+ve'),
        ('AB+', 'AB+ve'),
        ('A-', 'A-ve'),
        ('B-', 'B-ve'),
        ('O-', 'O-ve'),
        ('AB-', 'AB-ve')
    ], string='Blood Group')
    gender = fields.Selection([
        ('m', 'Male'),
        ('f', 'Female'),
        ('o', 'Other')
    ], 'Gender', required=True, default='m')
    nationality = fields.Many2one('res.country', 'Nationality')
    emergency_contact = fields.Many2one('res.partner', 'Emergency Contact')
    visa_info = fields.Char('Visa Info', size=64)
    id_number = fields.Char('ID Card Number', size=64)
    partner_id = fields.Many2one('res.partner', 'Partner',
                                 required=True, ondelete="cascade")
    user_id = fields.Many2one('res.users', 'User', ondelete="cascade")
    gr_no = fields.Char("Registration Number", copy=False, readonly=0)
    category_id = fields.Many2one('op.category', 'Category')
    course_detail_ids = fields.One2many('op.student.course', 'student_id',
                                        'Course Details',
                                        tracking=True)
    state = fields.Selection([('confirm', 'Confirm'), ('batch_allocated', 'Batch Allocated'),
                              ('stoped', 'Stoped')],
                             string="Status", default="confirm")
    active = fields.Boolean(default=True)
    batch_id = fields.Many2one('op.batch', string="Batch", required=1)
    fee_type = fields.Selection([('lump_sum_fee', 'Lump Sum Fee'), ('installment', 'Installment')], string="Fee Type", required=1)
    # branch_id = fields.Many2one('logic.branches', string="Branch")
    course_id = fields.Many2one('op.course', string="Course", compute="_compute_course_id", store=1)
    wallet_balance = fields.Float(string="Wallet Balance", readonly=1)
    batch_fee = fields.Float(string="Batch Fee", compute="_compute_batch_fee", store=1)
    discount = fields.Float(string="Discount", compute="_compute_batch_fee", store=1)
    total_payable_tax = fields.Float(string="Total Payable (Inc. Tax)", compute="_compute_batch_fee", store=1)
    paid_amount = fields.Float(string="Paid (Inc. Tax)", compute="_compute_batch_fee", store=1)
    due_amount = fields.Float(string="Due Amount (Inc. Tax)", compute="_compute_due_amount", store=1)
    payment_ids = fields.One2many('fee.payment.history', 'payment_id', string="Payment History")
    parent_name = fields.Char(string="Parent Name")
    parent_whatsapp = fields.Char(string="Parent Whatsapp")
    parent_email = fields.Char(string="Parent Email")
    father_name = fields.Char(string="Father Name")
    father_number = fields.Char(string="Father Number")
    mother_name = fields.Char(string="Mother Name")
    mother_number = fields.Char(string="Mother Number")
    admission_fee_paid = fields.Boolean(string="Paid Admission Fee")

    @api.model
    def create(self, vals):
        # if vals.get('gr_no') in [False, "New"]:
            # current_year = datetime.today().year
            # prefix = f"L{current_year}/"
            #
            # # Find the last record with the same year pattern
            # last_batch = self.search([('gr_no', 'like', prefix + '%')], order='gr_no desc', limit=1)
            # if last_batch and last_batch.gr_no:
            #     match = re.search(r"/(\d+)$", last_batch.gr_no)
            #     last_number = int(match.group(1)) if match else 0
            # else:
            #     last_number = 0
            #
            # new_number = last_number + 1
            # vals['gr_no'] = f"{prefix}{new_number}"
            # print(vals['gr_no'], 'Generated GR No')  # Debugging output

        student = super(OpStudent, self).create(vals)

        if student.batch_id:
            student.batch_id.total_no_of_students += 1
            student.batch_id.sudo().write({
                'student_ids': [(0, 0, {
                    'student_id': student.id,
                    'student_name': student.id,
                    'mobile': student.mobile,
                    'date_of_admission': student.admission_date
                })]
            })

        return student

    def write(self, vals):
        for student in self:
            old_batch = student.batch_id
            res = super(OpStudent, self).write(vals)
            new_batch = self.batch_id if 'batch_id' in vals else old_batch
            if old_batch and old_batch != new_batch:
                old_batch.total_no_of_students -= 1
                for i in old_batch.student_ids:
                    if i.student_name.id == self.id:
                        print('remove')
                        student_to_remove = old_batch.student_ids.filtered(lambda s: s.student_name.id == student.id)
                        print(student_to_remove, 'remove name')
                        old_batch.sudo().write({'student_ids': [(3, student_to_remove.id)]})
                    # unlink(old_batch.student_ids.student_name.id)
            if new_batch and new_batch != old_batch:
                print('hiiiiii')
                new_batch.total_no_of_students += 1
                # Check if the student already exists in `student_ids` before adding
                existing_student = new_batch.student_ids.filtered(lambda s: s.student_name.id == student.id)
                if not existing_student:
                    new_batch.sudo().write({
                        'student_ids': [(0, 0, {
                            'student_id': student.id,
                            'student_name': student.id,
                            'mobile': student.mobile,
                            'date_of_admission': student.admission_date,
                        })]
                    })


            return res

    def unlink(self):
        for student in self:
            if student.batch_id:
                student.batch_id.total_no_of_students -= 1
                student_to_remove = student.batch_id.student_ids.filtered(lambda s: s.student_name.id == student.id)
                print(student_to_remove, 'remove name')
                student.batch_id.sudo().write({'student_ids': [(3, student_to_remove.id)]})
        return super(OpStudent, self).unlink()


    # _sql_constraints = [(
    #     'unique_gr_no',
    #     'unique(gr_no)',
    #     'Registration Number must be unique per student!'
    # )]

    @api.depends('batch_id')
    def _compute_course_id(self):
        for rec in self:
            if rec.batch_id:
                rec.course_id = rec.batch_id.course_id.id
                rec.branch_id = rec.batch_id.branch.id

    # @api.onchange('batch_id', 'discount', 'total_payable_tax', 'paid_amount', )
    # def _onchange_batch_fee(self):
    #     if self.batch_id:
    #         self.batch_fee = self.batch_id.total_lump_sum_fee
    #         if self.discount == 0:
    #             self.total_payable_tax = self.batch_id.total_lump_sum_fee
    #         else:
    #             self.total_payable_tax = self.batch_id.total_lump_sum_fee - self.discount
    #         self.due_amount = self.total_payable_tax - self.paid_amount

    # @api.onchange('first_name', 'middle_name', 'last_name')
    # def _onchange_name(self):
    #     if not self.middle_name:
    #         self.name = str(self.first_name) + " " + str(
    #             self.last_name
    #         )
    #     else:
    #         self.name = str(self.first_name) + " " + str(
    #             self.middle_name) + " " + str(self.last_name)

    @api.depends('paid_amount','total_payable_tax')
    def _compute_due_amount(self):
        for i in self:
            i.due_amount = i.total_payable_tax - i.paid_amount

    @api.depends('fee_type','batch_id', 'batch_fee','discount','total_payable_tax','paid_amount','due_amount')
    def _compute_batch_fee(self):
        print('jjjjj')
        if self.fee_type:
            if self.fee_type == 'lump_sum_fee':
                self.batch_fee = self.batch_id.total_lump_sum_fee
            if self.fee_type == 'installment':
                self.batch_fee = self.batch_id.total_installment_fee

        if self.batch_fee != 0:
            print('kkkl')
            if self.discount == 0:
                self.total_payable_tax = self.batch_fee
            else:
                self.total_payable_tax = self.batch_fee - self.discount

    @api.constrains('birth_date')
    def _check_birthdate(self):
        for record in self:
            if record.birth_date:
                if record.birth_date > fields.Date.today():
                    raise ValidationError(_(
                        "Birth Date can't be greater than current date!"))

    @api.onchange('email')
    def _validate_email(self):
        if self.email and not tools.single_email_re.match(self.email):
            raise ValidationError(_('Invalid Email! Please enter a valid email address.'))

    @api.onchange("mobile")
    def _validate_mobile(self):
        if self.mobile and self.mobile.isalpha():
            raise ValidationError(_("Enter Your Valid Mobile Number"))

    def act_add_amount_to_wallet(self):
        active_id = self.env.context.get('active_id')
        fee = self.env['fee.quick.pay'].browse(active_id)
        print('hi', fee.amount)
        self.wallet_balance = fee.amount
        fee.state = 'done'
        fee.student_id = self.id
        # report = self.env['invoice.reports'].sudo().create({
        #     'lead_id': self.lead_id.id,
        #     'name': fee.name,
        #     'branch': self.branch_id.name,
        #     'date': date.today(),
        #
        # })

    @api.model
    def get_import_templates(self):
        return [{
            'label': _('Import Template for Students'),
            'template': '/openeducat_core/static/xls/op_student.xls'
        }]

    def create_student_user(self):
        user_group = self.env.ref("base.group_portal") or False
        users_res = self.env['res.users']
        for record in self:
            if not record.user_id:
                user_id = users_res.create({
                    'name': record.name,
                    'partner_id': record.partner_id.id,
                    'login': record.email,
                    'groups_id': user_group,
                    'is_student': True,
                    'tz': self._context.get('tz'),
                })
                record.user_id = user_id

    def act_allocate_to_batch(self):
        if self.batch_id:
            if self.fee_type:
                batch = self.env['op.batch'].sudo().search([('id', '=', self.batch_id.id)])
                batch.sudo().write({
                    'student_ids': [
                        (0, 0, {'student_id': self.id, 'student_name': self.id, 'date_of_admission': self.admission_date,
                                'mobile': self.mobile}),  # Add valid data
                    ]
                })
                self.state = 'batch_allocated'
                print(batch, 'batch')
            else:
                raise ValidationError("Kindly assign a fee type to this student.")
        else:
            raise ValidationError("Kindly assign a batch to this student.")

    def act_drop_student(self):
        self.state = 'stoped'

    def act_change_fee_plan(self):
        print('k')
        return {'type': 'ir.actions.act_window',
                'name': _('Change Plan'),
                'res_model': 'change.payment.plan',
                'target': 'new',
                'view_mode': 'form',
                'view_type': 'form',
                'context': {'default_student_id': self.id,
                            'default_fee_type': self.fee_type,
                            'default_batch_id': self.batch_id.id}, }

    admission_fee = fields.Float(string="Admission Fee")
    fee_type = fields.Selection(
        [('lump_sum_fee', 'Lump Sum Fee'), ('installment', 'Installment'), ('loan_fee', 'Loan')], string="Fee Type")

    def act_collect_fee(self):
        print('hi')
        return {'type': 'ir.actions.act_window',
                'name': _('Fee Collection'),
                'res_model': 'fee.collection.wizard',
                'target': 'new',
                'view_mode': 'form',
                'view_type': 'form',
                'context': {'default_collection_id': self.id,
                            'default_wallet_amount': self.wallet_balance, }, }


class FeeCollectionWizard(models.TransientModel):
    """This model is used for sending WhatsApp messages through Odoo."""
    _name = 'fee.collection.wizard'
    _description = "Fee Collection Wizard"

    fee_type = fields.Selection(
        [('Ancillary Fee(Non Taxable)', 'Ancillary Fee(Non Taxable)'), ('Other Fee', 'Other Fee'),
         ('Batch Fee', 'Batch Fee')],
        string="Fee Type", required=1)
    remarks = fields.Text(string="Remarks")
    amount_inc_tax = fields.Float(string="Amount (Inc. Tax)")
    tax = fields.Float(string="Tax")
    amount_exc_tax = fields.Float(string="Amount (Exc. Tax)")
    collection_id = fields.Many2one('op.student', string="Collection Record")
    payment_mode = fields.Selection(
        [('Cash', 'Cash'), ('Cheque', 'Cheque'), ('Online', 'Online'), ('Wallet', 'Wallet'), ('Bajaj', 'Bajaj')],
        string="Payment Mode", default="Wallet")
    branch = fields.Selection(
        [('Corporate Office & City Campus', 'Corporate Office & City Campus'), ('Cochin Campus', 'Cochin Campus'), ('Calicut Campus', 'Calicut Campus'), ('Trivandrum Campus', 'Trivandrum Campus'), ('Kottayam Campus', 'Kottayam Campus'),
         ('Perinthalmanna Branch', 'Perinthalmanna Branch'), ('Bangalore Campus', 'Bangalore Campus')], string="Branch")
    cheque_no = fields.Char(string="Cheque No/Reference No")
    wallet_amount = fields.Float(string="Wallet Amount", readonly=1)
    fee_name = fields.Selection(
        [('IMA Membership Fee', 'IMA Membership Fee'), ('IMA Exam Fee', 'IMA Exam Fee'),
         ('ACCA Exam Fee', 'ACCA Exam Fee'), ('ACCA Board Registration', 'ACCA Board Registration')], string="Fee Name")
    other_fee = fields.Selection(
        [('Admission Fee', 'Admission Fee'), ('Coaching Fee 1st Installment', 'Coaching Fee 1st Installment'),
         ('Coaching Fee 2nd Installment', 'Coaching Fee 2nd Installment'),
         ('Coaching Fee 3rd Installment', 'Coaching Fee 3rd Installment')], string="Fee Name")
    currency_id = fields.Many2one('res.currency', default=lambda self: self.env.company.currency_id)
    tax_id = fields.Many2one('account.tax', string="Tax")
    non_tax = fields.Boolean(string="Non Taxable")
    batch_id = fields.Many2one('op.batch', string="Batch")
    cgst_amount = fields.Float(string="CGST Amount")
    sgst_amount = fields.Float(string="SGST Amount")
    total_amount = fields.Float(string="Total Amount", compute="_compute_total_amount", store=1)

    @api.onchange('fee_type','other_fee','amount_exc_tax')
    def _onchange_fee_types(self):
        if self.fee_type == 'Other Fee':
            if self.other_fee == 'Admission Fee':
                self.amount_inc_tax = self.collection_id.batch_id.adm_inc_fee
                self.amount_exc_tax = self.collection_id.batch_id.adm_exc_fee
        if self.fee_type == 'Ancillary Fee(Non Taxable)':
            print('anc')
            # self.amount_inc_tax = self.amount_exc_tax
            self.tax = 0
            self.other_fee = False
            self.batch_id = False

        elif self.fee_type == 'Other Fee':
            self.fee_name = False
            self.batch_id = False
        else:
            self.batch_id = self.collection_id.batch_id.id
            self.fee_name = False
            self.other_fee = False


    @api.onchange('amount_inc_tax')
    def _onchange_amount_tax(self):
        tax = self.env['account.tax'].sudo().search([('name', '=', 'GST')], limit=1)
        if self.fee_type != 'Ancillary Fee(Non Taxable)':
            if self.amount_inc_tax > 0 and tax:
                tax_amount = 0  # Default tax percentage
                if tax.amount_type == 'group':
                    tax_amount += sum(t.amount for t in tax.children_tax_ids)
                print(tax_amount, 'tax')
                self.tax_id = tax.id
                print('tax_amt', self.amount_inc_tax * tax_amount / 100)
                current_tax = self.amount_inc_tax * tax_amount / 100
                # Reverse calculation to get amount_exc_tax
                self.amount_exc_tax = self.amount_inc_tax - current_tax
                self.tax = self.amount_inc_tax * tax_amount / 100

                # Split tax into CGST and SGST
                self.cgst_amount = self.tax / 2
                self.sgst_amount = self.tax / 2
            else:
                # self.amount_exc_tax = 0
                self.tax = 0
                self.cgst_amount = 0
                self.sgst_amount = 0
        # else:
        #     self.amount_inc_tax = self.amount_exc_tax


    @api.depends('amount_exc_tax','amount_inc_tax','fee_type')
    def _compute_total_amount(self):
        for rec in self:
            if rec.fee_type == 'Ancillary Fee(Non Taxable)':
                rec.total_amount = rec.amount_exc_tax
            else:
                rec.total_amount = rec.amount_inc_tax
    # @api.onchange('tax_id','amount_exc_tax','tax','non_tax','fee_type')
    # def _onchange_amount_tax(self):
    #     if self.fee_type != 'Ancillary Fee(Non Taxable)':
    #         if self.amount_exc_tax:
    #             tax_amount = 0
    #             tax = self.env['account.tax'].sudo().search([('name', '=', 'GST')])
    #             self.tax_id = tax.id
    #             print(tax.amount, 'amt')
    #             if tax.amount_type == 'group':
    #                 for i in tax.children_tax_ids:
    #                     tax_amount += i.amount
    #                     print(i.name, 'jjjjj')
    #             self.tax = self.amount_exc_tax * tax_amount / 100
    #
    #     elif self.non_tax == 1:
    #         self.tax_id = False
    #         self.tax = 0
    #
    #     self.amount_inc_tax = self.amount_exc_tax + self.tax
    #     if self.tax != 0:
    #         self.cgst_amount = self.tax / 2
    #         self.sgst_amount = self.tax / 2
        # if self.amount_inc_tax and self.amount_exc_tax:
        #     self.tax = self.amount_inc_tax - self.amount_exc_tax
    # @api.onchange('amount_exc_tax', 'tax_id', 'non_tax', 'fee_type')
    # def _onchange_amount_tax(self):
    #     """Calculate tax and update amount_inc_tax"""
    #     if self.fee_type != 'Ancillary Fee(Non Taxable)':
    #         if self.amount_exc_tax:
    #             tax_amount = 18  # Default tax percentage
    #
    #             tax = self.env['account.tax'].sudo().search([('name', '=', 'GST')], limit=1)
    #             if tax:
    #                 self.tax_id = tax.id
    #                 if tax.amount_type == 'group':
    #                     tax_amount = sum(t.amount for t in tax.children_tax_ids)
    #
    #             self.tax = self.amount_exc_tax * tax_amount / 100
    #
    #     elif self.non_tax:
    #         self.tax_id = False
    #         self.tax = 0
    #
    #     self.amount_inc_tax = self.amount_exc_tax + self.tax
    #     if self.tax > 0:
    #         self.cgst_amount = self.tax / 2
    #         self.sgst_amount = self.tax / 2
    #     else:
    #         self.cgst_amount = 0
    #         self.sgst_amount = 0

    # def act_submit(self):
    #     print('hhi')
    #
    #     if self.fee_type == 'Other Fee' and self.other_fee == 'Admission Fee':
    #         if self.collection_id.admission_fee_paid == False:
    #             if self.amount_inc_tax != self.collection_id.batch_id.adm_inc_fee:
    #                 raise exceptions.ValidationError("Invalid amount. Please enter the correct admission fee.")
    #             else:
    #                 report = self.env['invoice.reports'].sudo().create({
    #                     'name': self.collection_id.name,
    #                     'branch': self.collection_id.branch_id.name,
    #                     'date': date.today(),
    #                     'fee_type': self.fee_name,
    #                     'reference_no': self.cheque_no,
    #                     'amount_inc_tax': self.amount_inc_tax,
    #                     'fee_collected_by': self.env.user.id,
    #                     'lead_id': self.collection_id.lead_id.id
    #                 })
    #                 last_report = self.env['invoice.reports'].sudo().search([], order="id desc", limit=1)
    #                 self.collection_id.lead_id.admission_amount = self.collection_id.lead_id.admission_amount + self.amount_inc_tax
    #                 self.collection_id.lead_id.receipt_no = last_report.invoice_number
    #                 self.collection_id.lead_id.date_of_receipt = date.today()
    #                 self.collection_id.admission_fee_paid = True
    #                 self.collection_id.admission_fee = self.amount_inc_tax
    #         else:
    #             raise exceptions.UserError("Admission fee has already been paid!")
    #     else:
    #
    #         if self.fee_type == 'Ancillary Fee(Non Taxable)':
    #             report = self.env['invoice.reports'].sudo().create({
    #                 'name': self.collection_id.name,
    #                 'branch': self.collection_id.branch_id.name,
    #                 'date': date.today(),
    #                 'fee_type': self.fee_name,
    #                 'reference_no': self.cheque_no,
    #                 'amount_inc_tax': self.amount_inc_tax,
    #                 'fee_collected_by': self.env.user.id,
    #                 'lead_id': self.collection_id.lead_id.id
    #             })
    #         if self.fee_type == 'Other Fee':
    #
    #             report = self.env['invoice.reports'].sudo().create({
    #                 'name': self.collection_id.name,
    #                 'branch': self.collection_id.branch_id.name,
    #                 'date': date.today(),
    #                 'fee_type': self.other_fee,
    #                 'reference_no': self.cheque_no,
    #                 'amount_inc_tax': self.amount_inc_tax,
    #                 'fee_collected_by': self.env.user.id,
    #                 'lead_id': self.collection_id.lead_id.id
    #             })
    #
    #         if self.fee_type == 'Batch Fee':
    #             report = self.env['invoice.reports'].sudo().create({
    #                 'name': self.collection_id.name,
    #                 'branch': self.collection_id.branch_id.name,
    #                 'date': date.today(),
    #                 'fee_type': 'Batch Fee',
    #                 'reference_no': self.cheque_no,
    #                 'amount_inc_tax': self.amount_inc_tax,
    #                 'fee_collected_by': self.env.user.id,
    #                 'lead_id': self.collection_id.lead_id.id
    #             })
    #         if self.payment_mode == 'Wallet':
    #             if self.collection_id.wallet_balance == 0:
    #                 raise UserError("Student Wallet Amount is 0")
    #             else:
    #                 student = self.env['op.student'].browse(self.collection_id.id)
    #
    #                 # Ensure the record exists and the `collection_id` is correctly set
    #                 if student:
    #
    #                     if self.amount_inc_tax != 0:
    #                         if self.collection_id.wallet_balance >= self.amount_inc_tax:
    #
    #                             self.collection_id.wallet_balance = self.collection_id.wallet_balance - self.amount_inc_tax
    #                             student.sudo().write({
    #                                 'payment_ids': [
    #                                     (0, 0, {
    #                                         'sl_no': 1,
    #                                         'date': fields.Datetime.now(),
    #                                         'payment_mode': self.payment_mode,
    #                                         'fee_type': self.fee_type,  # Adjust field name if necessary
    #                                         'amount_exc_tax': self.amount_exc_tax,
    #                                         'amount_inc_tax': self.amount_inc_tax,
    #                                         'cheque_no': self.cheque_no,
    #                                         'branch': self.branch,
    #                                         'fee_name': self.fee_name or self.other_fee or 'Batch Fee',
    #                                         'tax_amount': self.tax,
    #                                         'cgst_amount': self.cgst_amount,
    #                                         'sgst_amount': self.sgst_amount
    #                                     }),
    #                                 ]
    #                             })
    #
    #                             if self.other_fee:
    #                                 if self.other_fee == 'Admission Fee':
    #                                     self.collection_id.admission_fee = self.amount_inc_tax
    #
    #                             if self.fee_type == 'Batch Fee':
    #                                 if self.collection_id.paid_amount == 0:
    #                                     self.collection_id.paid_amount = self.amount_inc_tax
    #
    #                                 else:
    #                                     self.collection_id.paid_amount = self.collection_id.paid_amount + self.amount_inc_tax
    #
    #                             if self.fee_type == 'Other Fee':
    #                                 if self.fee_name != 'Admission Fee':
    #                                     self.collection_id.paid_amount = self.collection_id.paid_amount + self.amount_inc_tax
    #                                     print('ooo')
    #
    #
    #                         else:
    #                             raise ValidationError(_(
    #                                 "Invalid Wallet Amount!"))
    #                     else:
    #                         if self.collection_id.wallet_balance >= self.amount_inc_tax:
    #                             self.collection_id.wallet_balance = self.collection_id.wallet_balance - self.amount_inc_tax
    #
    #                             student.sudo().write({
    #                                 'payment_ids': [
    #                                     (0, 0, {
    #                                         'sl_no': 1,
    #                                         'date': fields.Datetime.now(),
    #                                         'payment_mode': self.payment_mode,
    #                                         'fee_type': self.fee_type,  # Adjust field name if necessary
    #                                         'amount_exc_tax': self.amount_exc_tax,
    #                                         'amount_inc_tax': self.amount_inc_tax,
    #                                         'cheque_no': self.cheque_no,
    #                                         'branch': self.branch,
    #                                         'fee_name': self.fee_name or self.other_fee or 'Batch Fee',
    #                                         'tax_amount': self.tax,
    #                                         'cgst_amount': self.cgst_amount,
    #                                         'sgst_amount': self.sgst_amount
    #                                     }),
    #                                 ]
    #                             })
    #
    #                             if self.other_fee:
    #                                 if self.other_fee == 'Admission Fee':
    #                                     self.collection_id.admission_fee = self.collection_id.admission_fee + self.amount_inc_tax
    #
    #                             if self.fee_type == 'Batch Fee':
    #                                 self.collection_id.paid_amount = self.collection_id.paid_amount + self.amount_inc_tax
    #
    #                         else:
    #                             raise UserError('Invalid Wallet Amount.')
    #         else:
    #             student = self.env['op.student'].browse(self.collection_id.id)
    #
    #             # Ensure the record exists and the `collection_id` is correctly set
    #             if student:
    #                 student.sudo().write({
    #                     'payment_ids': [
    #                         (0, 0, {
    #                             'sl_no': 1,
    #                             'date': fields.Datetime.now(),
    #                             'payment_mode': self.payment_mode,
    #                             'fee_type': self.fee_type,  # Adjust field name if necessary
    #                             'amount_exc_tax': self.amount_exc_tax,
    #                             'amount_inc_tax': self.amount_inc_tax,
    #                             'cheque_no': self.cheque_no,
    #                             'branch': self.branch,
    #                             'fee_name': self.fee_name or self.other_fee or 'Batch Fee',
    #                             'tax_amount': self.tax,
    #                             'cgst_amount': self.cgst_amount,
    #                             'sgst_amount': self.sgst_amount,
    #                         }),
    #                     ]
    #                 })
    #
    #                 if self.other_fee:
    #                     if self.other_fee == 'Admission Fee':
    #                         self.collection_id.admission_fee = self.amount_inc_tax
    #
    #
    #                 if self.fee_type == 'Batch Fee':
    #                     self.collection_id.paid_amount = self.collection_id.paid_amount + self.amount_exc_tax

    def act_submit(self):
        print('hhi')

        if self.fee_type == 'Other Fee' and self.other_fee == 'Admission Fee':
            if self.collection_id.admission_fee_paid:
                raise UserError("Admission fee has already been paid!")

            if self.amount_inc_tax != self.collection_id.batch_id.adm_inc_fee:
                raise ValidationError("Invalid amount. Please enter the correct admission fee.")

            report = self.create_invoice_report(self.other_fee)
            self.update_admission_fee(report)

        else:
            report = self.create_invoice_report(self.fee_name if self.fee_type != 'Other Fee' else self.other_fee)
            self.handle_wallet_payment()
            self.update_student_payment()

        # 🛑 Ensure payment record is created only once
        self.create_payment_record()

    def create_invoice_report(self, fee_type):
        print(self.amount_exc_tax, 'rrrr')
        if self.amount_exc_tax != 0:
            exc_tax = self.amount_exc_tax
            print(exc_tax, 'ancill')
        else:
            exc_tax = self.amount_inc_tax - self.tax
            print(exc_tax, 'withot')
        return self.env['invoice.reports'].sudo().create({
            'name': self.collection_id.name,
            'branch': self.collection_id.branch_id.name,
            'date': date.today(),
            'fee_type': self.fee_type,
            'reference_no': self.cheque_no,
            'amount_inc_tax': self.amount_inc_tax,
            'fee_collected_by': self.env.user.id,
            'lead_id': self.collection_id.lead_id.id,
            'payment_mode': self.payment_mode,
            'cheque_no': self.cheque_no,
            'batch': self.collection_id.batch_id.name,
            'student_id': self.collection_id.id,
            'cgst_amount': self.cgst_amount,
            'sgst_amount': self.sgst_amount,
            'fee_name': self.other_fee or self.fee_name or 'Batch Fee',
            'tax': self.tax,
            'amount_exc_tax': exc_tax

        })


    def update_admission_fee(self, report):
        last_report = self.env['invoice.reports'].sudo().search([], order="id desc", limit=1)
        lead = self.collection_id.lead_id

        lead.admission_amount += self.amount_inc_tax
        lead.receipt_no = last_report.invoice_number
        lead.date_of_receipt = date.today()
        lead.report = last_report.id
        self.collection_id.admission_fee_paid = True
        self.collection_id.admission_fee = self.amount_inc_tax

    def handle_wallet_payment(self):
        if self.payment_mode == 'Wallet':
            if self.collection_id.wallet_balance == 0:
                raise UserError("Student Wallet Amount is 0")

            if self.collection_id.wallet_balance < self.total_amount:
                raise ValidationError("Invalid Wallet Amount!")

            self.collection_id.wallet_balance -= self.total_amount
            if self.other_fee == 'Admission Fee':
                self.collection_id.admission_fee += self.amount_inc_tax

    def update_student_payment(self):
        if self.other_fee == 'Admission Fee':
            self.collection_id.admission_fee = self.amount_inc_tax
        if self.fee_type == 'Batch Fee':
            self.collection_id.paid_amount += self.amount_inc_tax

    def create_payment_record(self):
        student = self.env['op.student'].browse(self.collection_id.id)
        if student:
            student.sudo().write({'payment_ids': [(0, 0, self.get_payment_data())]})

    def get_payment_data(self):
        last_sl_no = len(self.collection_id.payment_ids) + 1
        last_report = self.env['invoice.reports'].sudo().search([], order="id desc", limit=1)
        if self.amount_exc_tax != 0:
            exc_tax = self.amount_exc_tax
        else:
            exc_tax = self.amount_inc_tax - self.tax
        return {
            'sl_no': last_sl_no,
            'date': fields.Datetime.now(),
            'payment_mode': self.payment_mode,
            'fee_type': self.fee_type,
            'amount_exc_tax': exc_tax,
            'amount_inc_tax': self.amount_inc_tax,
            'cheque_no': self.cheque_no,
            'branch': self.branch,
            'fee_name': self.fee_name or self.other_fee or 'Batch Fee',
            'tax_amount': self.tax,
            'cgst_amount': self.cgst_amount,
            'sgst_amount': self.sgst_amount,
            'total_amount': self.total_amount,
            'invoice_no': last_report.invoice_number,
        }

    @api.onchange('payment_mode')
    def _onchange_payment_mode(self):
        if self.payment_mode:
            if self.payment_mode == 'Cash':
                self.cheque_no = False
            else:
                self.branch = False


class PaymentHistoryFeeCollection(models.Model):
    _name = 'fee.payment.history'

    sl_no = fields.Integer(string="No")
    date = fields.Datetime(string="Date")
    payment_mode = fields.Char(string="Payment Mode")
    # payment_type = fields.Char(string="Payment Type")
    fee_type = fields.Char(string="Fee Type")
    invoice_no = fields.Char(string="Invoice No")
    reference_no = fields.Char(string="Reference No")
    amount_exc_tax = fields.Float(string="Amount (Exc. Tax)")
    amount_inc_tax = fields.Float(string="Amount (Inc. Tax)")
    fee_name = fields.Char(string="Fee Name")
    payment_id = fields.Many2one('op.student', string="Payment")
    company_id = fields.Many2one(string='Company', comodel_name='res.company', default=lambda self: self.env.company)
    cgst_amount = fields.Float(string="CGST Amount")
    sgst_amount = fields.Float(string="SGST Amount")
    currency_id = fields.Many2one(
        'res.currency',
        string="Currency",
        default=lambda self: self.env.company.currency_id.id
    )
    total_amount = fields.Float(string="Paid Amount")
    branch = fields.Selection(
        [('Corporate Office & City Campus', 'Corporate Office & City Campus'), ('Cochin Campus', 'Cochin Campus'),
         ('Calicut Campus', 'Calicut Campus'), ('Trivandrum Campus', 'Trivandrum Campus'),
         ('Kottayam Campus', 'Kottayam Campus'),
         ('Perinthalmanna Branch', 'Perinthalmanna Branch'), ('Bangalore Campus', 'Bangalore Campus')], string="Branch")
    cheque_no = fields.Char(string="Cheque No/Reference No")
    tax_amount = fields.Float(string="Tax")
    amount_in_words = fields.Char(string="Amount in Words", compute="_compute_amount_in_words", store=1)
    amount_in_words_non_tax = fields.Char(string="Amount in Words", compute="_compute_amount_in_words_non_tax", store=1)

    # @api.depends('amount_inc_tax', 'currency_id')
    # def _compute_amount_in_words(self):
    #     for record in self:
    #         # Convert the amount to words, specifying the language and currency
    #         if record.currency_id:
    #             record.amount_in_words = amount_to_text(
    #                 record.amount_inc_tax,
    #                 lang=self.env.user.lang or 'en',
    #                 currency=record.currency_id.name
    #             )
    #         else:
    #             record.amount_in_words = amount_to_text(
    #                 record.amount_inc_tax,
    #                 lang=self.env.user.lang or 'en'
    #             )

    @api.depends('amount_inc_tax')
    def _compute_amount_in_words(self):
        print('workssssss')
        for i in self:

            i.amount_in_words = num2words(i.amount_inc_tax, lang='en').upper()
        # print(f"Amount in words: {amount_in_words}")

    @api.depends('total_amount')
    def _compute_amount_in_words_non_tax(self):
        print('workssssss')
        for i in self:
            i.amount_in_words_non_tax = num2words(i.total_amount, lang='en').upper()

    def act_print_invoice(self):
        # print('hi')
        # print(self.env.context)
        # data = {
        #     'model_id': self.id,
        #     'form': self.env.context
        # }

        return self.env.ref('logic_base_17.action_report_students_payment_history').report_action(self)


    def act_print_invoice_non_taxable(self):

        return self.env.ref('logic_base_17.action_report_students_payment_history_non_taxable').report_action(self)
