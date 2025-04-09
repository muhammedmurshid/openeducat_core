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
                              ('stoped', 'Droped')],
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
    payment_ids = fields.One2many('fee.payment.history', 'payment_id', string="Payment History")
    parent_name = fields.Char(string="Parent Name")
    parent_whatsapp = fields.Char(string="Parent Whatsapp")
    parent_email = fields.Char(string="Parent Email")
    father_name = fields.Char(string="Father Name")
    father_number = fields.Char(string="Father Number")
    mother_name = fields.Char(string="Mother Name")
    mother_number = fields.Char(string="Mother Number")
    admission_fee_paid = fields.Boolean(string="Paid Admission Fee")
    closing_balance = fields.Float(string="Receivable as per ERP on 31/03/2025 (Debit)")
    credit_balance_erp = fields.Float(string="Balance in ERP Wallet Amount 31/03/2025 (Credit)")

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
            if student.fee_type == 'lump_sum_fee':
                student.due_amount = student.batch_id.total_lump_sum_fee
            elif student.fee_type == 'installment':
                student.due_amount = student.batch_id.total_installment_fee

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

    # @api.depends('payment_ids.balance')
    # def _compute_due_amount(self):
    #     for rec in self:
    #         if rec.payment_ids:
    #             last_balance = rec.payment_ids[-1].balance
    #             if rec.payment_ids[-1].balance_type == 'debit':
    #                 rec.due_amount = abs(last_balance)  # Ensure it's positive
    #             else:
    #                 rec.due_amount = -abs(last_balance)

    due_amount = fields.Float(string="Due Amount (Inc. Tax)")


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
        self.wallet_balance += fee.amount
        fee.receipt_no = fee._generate_receipt_number()
        fee.state = 'done'
        fee.student_id = self.id
        fee.assigned_by = self.env.user.id
        fee.assigned_date = fields.Datetime.now()

        receipt = self.env['receipts.report'].sudo().create({
            'date': fields.Datetime.now(),
            'amount': fee.amount,
            'name': self.name,
            'branch': '',
            'payment_mode': 'Gateway',
            'student_id': self.id,
            'batch': self.batch_id.name

        })



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

    def get_current_wallet_collection(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': 'Wallet Collections',
            'view_mode': 'tree,form',
            'res_model': 'fee.quick.pay',
            'domain': [('student_id', '=', self.id)],
            'context': "{'create': False}"
        }

    def act_create_receipt(self):
        print('hi')
        return {'type': 'ir.actions.act_window',
                'name': _('Create Receipt'),
                'res_model': 'create.receipt.wizard',
                'target': 'new',
                'view_mode': 'form',
                'view_type': 'form',
                'context': {'default_student_id': self.id}, }

    def compute_count(self):
        for record in self:
            record.wallet_smart_count = self.env['fee.quick.pay'].sudo().search_count(
                [('student_id', '=', self.id)])

    wallet_smart_count = fields.Integer(compute='compute_count')

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
    drop_reason = fields.Text(string="Drop Reason")
    drop_date = fields.Date(string="Drop Date")
    drop_date_title = fields.Char(compute="_compute_drop_date_title")

    def _compute_drop_date_title(self):
        for record in self:
            record.drop_date_title = f"Drop Date: {record.drop_date.strftime('%Y-%m-%d')}" if record.drop_date else "No Drop Date"


    def act_drop_student(self):
        return {'type': 'ir.actions.act_window',
                'name': _('Drop'),
                'res_model': 'drop.student.wizard',
                'target': 'new',
                'view_mode': 'form',
                'view_type': 'form',
                'context': {'default_student_id': self.id}, }


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

    admission_fee = fields.Float(string="Admission Fee", related="batch_id.admission_fee")

    def act_add_closing_balance(self):
        for rec in self:
            rec.payment_ids = [(0, 0, {
                'sl_no': len(rec.payment_ids) + 1,  # Auto-increment SL No
                'date': datetime.strptime("01/04/2025", "%d/%m/%Y"),
                'voucher_name': 'Opening Balance',
                'payment_mode': 'Cash',  # Set a default or dynamic value
                'fee_type': 'Tuition Fee',  # Set a default or fetch dynamically
                'invoice_no': 'INV-001',  # Example, replace with real invoice number
                'reference_no': 'REF-001',
                'amount_exc_tax': 0,
                'amount_inc_tax': 0,
                'fee_name': 'Opening Balance',
                'debit_amount': rec.closing_balance,
                'credit_amount': rec.credit_balance_erp,
                'balance': rec.credit_balance_erp,  # Replace with actual calculation if needed

            })]
            rec.wallet_balance += rec.credit_balance_erp
            # rec.due_amount = rec.closing_balance


    def act_collect_fee(self):
        print('hi')
        return {'type': 'ir.actions.act_window',
                'name': _('Create Invoice'),
                'res_model': 'fee.collection.wizard',
                'target': 'new',
                'view_mode': 'form',
                'view_type': 'form',
                'context': {'default_collection_id': self.id,
                            'default_wallet_amount': self.wallet_balance, 'default_fee_plan': self.fee_type }, }


class FeeCollectionWizard(models.TransientModel):
    """This model is used for sending WhatsApp messages through Odoo."""
    _name = 'fee.collection.wizard'
    _description = "Fee Collection Wizard"

    fee_type = fields.Selection(
        [('Ancillary Fee(Non Taxable)', 'Ancillary Collection A/C'), ('Other Fee', 'Other Fee'),
         ('Batch Fee', 'Course Fee')],
        string="Fee Type", required=1)
    remarks = fields.Text(string="Remarks")
    amount_inc_tax = fields.Float(string="Amount (Inc. Tax)")
    tax = fields.Float(string="Tax")
    amount_exc_tax = fields.Float(string="Amount (Exc. Tax)")
    collection_id = fields.Many2one('op.student', string="Collection Record")
    place_of_supply = fields.Selection([
        ('AN', 'Andaman and Nicobar Islands'),
        ('AP', 'Andhra Pradesh'),
        ('AR', 'Arunachal Pradesh'),
        ('AS', 'Assam'),
        ('BR', 'Bihar'),
        ('CH', 'Chandigarh'),
        ('CG', 'Chhattisgarh'),
        ('DD', 'Daman and Diu'),
        ('DL', 'Delhi'),
        ('GA', 'Goa'),
        ('GJ', 'Gujarat'),
        ('HR', 'Haryana'),
        ('HP', 'Himachal Pradesh'),
        ('JH', 'Jharkhand'),
        ('JK', 'Jammu and Kashmir'),
        ('KA', 'Karnataka'),
        ('KL', 'Kerala'),
        ('LD', 'Lakshadweep'),
        ('MP', 'Madhya Pradesh'),
        ('MH', 'Maharashtra'),
        ('MN', 'Manipur'),
        ('ML', 'Meghalaya'),
        ('MZ', 'Mizoram'),
        ('NL', 'Nagaland'),
        ('OR', 'Odisha'),
        ('PB', 'Punjab'),
        ('PY', 'Puducherry'),
        ('RJ', 'Rajasthan'),
        ('SK', 'Sikkim'),
        ('TN', 'Tamil Nadu'),
        ('TS', 'Telangana'),
        ('TR', 'Tripura'),
        ('UP', 'Uttar Pradesh'),
        ('UK', 'Uttarakhand'),
        ('WB', 'West Bengal'),
        ('FC','Foreign Country')
    ], string="Place of Supply", default='KL')
    payment_mode = fields.Selection(
        [('Wallet', 'Wallet')],
        string="Payment Mode", default="Wallet")
    branch = fields.Selection(
        [('Corporate Office & City Campus', 'Corporate Office & City Campus'), ('Cochin Campus', 'Cochin Campus'), ('Calicut Campus', 'Calicut Campus'), ('Trivandrum Campus', 'Trivandrum Campus'), ('Kottayam Campus', 'Kottayam Campus'),
         ('Perinthalmanna Branch', 'Perinthalmanna Branch'), ('Bangalore Campus', 'Bangalore Campus')], string="Branch")
    cheque_no = fields.Char(string="Cheque No/Reference No")
    wallet_amount = fields.Float(string="Amount in Wallet", readonly=1)
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
    igst_amount = fields.Float(string="IGST Amount")
    total_amount = fields.Float(string="Total Amount", compute="_compute_total_amount", store=1)
    fee_plan = fields.Char(string="Fee Plan")
    choose_payment_installment_plan = fields.Selection([('1st Installment','1st Installment'), ('2nd Installment','2nd Installment'), ('3rd Installment','3rd Installment')], string="Choose Installment Plan")

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

    @api.onchange('fee_plan','choose_payment_installment_plan')
    def _onchange_batch_fee_plan(self):
        if self.fee_plan != 'installment':
            self.choose_payment_installment_plan = False
            if self.fee_type != 'Ancillary Fee(Non Taxable)':
                self.amount_inc_tax = self.collection_id.due_amount
        else:
            if self.choose_payment_installment_plan == '1st Installment':
                self.amount_inc_tax = self.batch_id.installment_ids[0].amount_inc_installment if len(
                    self.batch_id.installment_ids) > 0 else 0

            elif self.choose_payment_installment_plan == '2nd Installment':
                self.amount_inc_tax = self.batch_id.installment_ids[1].amount_inc_installment if len(
                    self.batch_id.installment_ids) > 1 else 0

            elif self.choose_payment_installment_plan == '3rd Installment':
                self.amount_inc_tax = self.batch_id.installment_ids[2].amount_inc_installment if len(
                    self.batch_id.installment_ids) > 2 else 0
            else:
                self.amount_inc_tax = 0

    @api.onchange('amount_inc_tax')
    def _onchange_amount_tax(self):
        tax = self.env['account.tax'].sudo().search([('name', '=', 'GST')], limit=1)
        if self.fee_type != 'Ancillary Fee(Non Taxable)':
            if self.amount_inc_tax > 0 and tax:
                tax_amount = 0  # Default tax percentage
                # print(tax_amount, 'tax')
                # self.tax_id = tax.id
                print('tax_amt', self.amount_inc_tax * 18 / 118)
                current_tax = self.amount_inc_tax * 18 / 118
                # Reverse calculation to get amount_exc_tax
                self.amount_exc_tax = self.amount_inc_tax - current_tax
                self.tax = self.amount_inc_tax * 18 / 118

                # Split tax into CGST and SGST
                self.cgst_amount = self.tax / 2
                self.sgst_amount = self.tax / 2
                self.igst_amount = self.tax
            else:
                # self.amount_exc_tax = 0
                self.tax = 0
                self.igst_amount = self.tax
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

    def act_submit(self):
        print('hhi')
        self.handle_wallet_payment()

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
            'fee_name': self.other_fee or self.fee_name or self.choose_payment_installment_plan or 'Lump sum Fee',
            'tax': self.tax,
            'amount_exc_tax': exc_tax

        })


    def update_admission_fee(self, report):
        last_report = self.env['invoice.reports'].sudo().search([], order="id desc", limit=1)
        lead = self.collection_id.lead_id

        lead.admission_amount += self.amount_inc_tax
        lead.receipt_no = last_report.invoice_number
        lead.date_of_receipt = date.today()
        lead.state = 'qualified'
        lead.lead_quality = 'admission'

        lead.report = last_report.id
        self.collection_id.admission_fee_paid = True
        self.collection_id.admission_fee = self.amount_inc_tax
        if self.other_fee == 'Admission Fee':
            lead.admission_fee_paid = True

    def handle_wallet_payment(self):
        wallet_balance = self.collection_id.wallet_balance

        # Check if wallet has sufficient balance
        if wallet_balance < self.total_amount:
            # self.wallet_amount = 0  # Reset wallet amount shown in form
            raise UserError(f"Insufficient wallet balance. Available: {wallet_balance}, Required: {self.total_amount}")

        # Deduct total amount from wallet
        self.collection_id.wallet_balance -= self.total_amount


        # If it's Admission Fee, also update that field
        # if self.other_fee == 'Admission Fee':
        #     self.collection_id.admission_fee += self.amount_inc_tax
        # if self.fee_type == 'Ancillary Fee(Non Taxable)':
        #     if self.other_fee != 'Admission Fee':
        #         self.collection_id.due_amount -= self.total_amount

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
        # self.collection_id.due_amount = self.collection_id.wallet_balance - self.collection_id.due_amount
        last_sl_no = len(self.collection_id.payment_ids) + 1
        last_report = self.env['invoice.reports'].sudo().search([], order="id desc", limit=1)
        type = 'invoice'
        voucher_name = 'Receipt'
        if self.fee_type == 'Ancillary Fee(Non Taxable)':
            voucher_name = 'Collection A/c'
            type = 'ancillary'
        else:
            voucher_name = 'Invoice'
            type = 'invoice'
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
            'voucher_no': last_report.invoice_number,
            'voucher_name': voucher_name,
            'type': type,
            'cheque_no': self.cheque_no,
            'branch': self.branch,
            'fee_name': self.fee_name or self.other_fee or self.choose_payment_installment_plan or 'Lump sum Fee',
            'tax_amount': self.tax,
            'cgst_amount': self.cgst_amount,
            'sgst_amount': self.sgst_amount,
            'total_amount': self.total_amount,
            'debit_amount': self.total_amount,
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
    debit_amount = fields.Float(string="Debit Amount")
    credit_amount = fields.Float(string="Credit Amount")
    voucher_no = fields.Char(string="Voucher No.")
    voucher_name = fields.Char(string="Voucher Name")
    type = fields.Selection([('receipt','Receipt'), ('invoice','Invoice'),('ancillary','Ancillary'),('opening','Opening')], string="Type")
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

    balance = fields.Float(string="Balance", compute="_compute_balance_amount", store=True)
    balance_type = fields.Selection([('debit', 'Debit'), ('credit', 'Credit')], string="Balance Type", store=True)

    @api.depends('debit_amount', 'credit_amount')
    def _compute_balance_amount(self):
        for record in self:
            total_credit = sum(record.payment_id.payment_ids.mapped('credit_amount'))
            total_debit = sum(record.payment_id.payment_ids.mapped('debit_amount'))
            print(total_debit, 'total debit', total_credit)

            # Calculate balance
            if total_credit > total_debit:
                record.balance = total_credit - total_debit
                record.balance_type = 'credit'
            elif total_debit > total_credit:
                record.balance = total_debit - total_credit
                record.balance_type = 'debit'
            else:
                record.balance = 0
                record.balance_type = False  # No balance



    @api.depends('amount_inc_tax')
    def _compute_amount_in_words(self):
        print('workssssss')
        for i in self:

            i.amount_in_words = num2words(i.amount_inc_tax, lang='en').upper()
        # print(f"Amount in words: {amount_in_words}")

    @api.depends('credit_amount')
    def _compute_amount_in_words_non_tax(self):
        print('workssssss')
        for i in self:
            i.amount_in_words_non_tax = num2words(i.credit_amount, lang='en').upper()
            print(i.amount_in_words_non_tax, 'workssssss')

    def act_print_invoice(self):

        return self.env.ref('logic_base_17.action_report_students_payment_history').report_action(self)


    def act_print_invoice_non_taxable(self):

        return self.env.ref('logic_base_17.action_report_students_payment_history_non_taxable').report_action(self)
