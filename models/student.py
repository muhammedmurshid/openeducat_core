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

from odoo import models, fields, api, _, tools
from odoo.exceptions import ValidationError, UserError


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

    first_name = fields.Char('First Name', translate=True)
    middle_name = fields.Char('Middle Name', translate=True)
    last_name = fields.Char('Last Name', translate=True)
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
    gr_no = fields.Char("Registration Number", size=20)
    category_id = fields.Many2one('op.category', 'Category')
    course_detail_ids = fields.One2many('op.student.course', 'student_id',
                                        'Course Details',
                                        tracking=True)
    state = fields.Selection([('confirm', 'Confirm'), ('batch_allocated', 'Batch Allocated'),
                              ('stoped', 'Stoped')],
                             string="Status", default="confirm")
    active = fields.Boolean(default=True)
    batch_id = fields.Many2one('op.batch', string="Batch", required=1)
    # branch_id = fields.Many2one('logic.branches', string="Branch")
    course_id = fields.Many2one('op.course', string="Course")
    wallet_balance = fields.Float(string="Wallet Balance", readonly=1)
    batch_fee = fields.Float(string="Batch Fee")
    discount = fields.Float(string="Discount")
    total_payable_tax = fields.Float(string="Total Payable (Inc. Tax)")
    paid_amount = fields.Float(string="Paid (Inc. Tax)")
    due_amount = fields.Float(string="Due Amount (Inc. Tax)")
    payment_ids = fields.One2many('fee.payment.history', 'payment_id', string="Payment History")

    _sql_constraints = [(
        'unique_gr_no',
        'unique(gr_no)',
        'Registration Number must be unique per student!'
    )]

    @api.onchange('batch_id', 'discount', 'total_payable_tax', 'paid_amount', )
    def _onchange_batch_fee(self):
        if self.batch_id:
            self.batch_fee = self.batch_id.total_lump_sum_fee
            if self.discount == 0:
                self.total_payable_tax = self.batch_id.total_lump_sum_fee
            else:
                self.total_payable_tax = self.batch_id.total_lump_sum_fee - self.discount
            self.due_amount = self.total_payable_tax - self.paid_amount

    @api.onchange('first_name', 'middle_name', 'last_name')
    def _onchange_name(self):
        if not self.middle_name:
            self.name = str(self.first_name) + " " + str(
                self.last_name
            )
        else:
            self.name = str(self.first_name) + " " + str(
                self.middle_name) + " " + str(self.last_name)

    @api.constrains('birth_date')
    def _check_birthdate(self):
        for record in self:
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
            batch = self.env['op.batch'].sudo().search([('id', '=', self.batch_id.id)])
            batch.sudo().write({
                'student_ids': [
                    (0, 0, {'student_id': self.id, 'student_name': self.id}),  # Add valid data
                ]
            })
            self.state = 'batch_allocated'
            print(batch, 'batch')
        else:
            raise ValidationError("Kindly assign a batch to this student.")

    def act_drop_student(self):
        self.state = 'stoped'

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

    def act_submit(self):
        print('hhi')
        if self.payment_mode == 'Wallet':
            if self.collection_id.wallet_balance == 0:
                raise UserError("Student Wallet Amount is 0")
            else:
                student = self.env['op.student'].browse(self.collection_id.id)

                # Ensure the record exists and the `collection_id` is correctly set
                if student:

                    if self.amount_inc_tax != 0:
                        if self.collection_id.wallet_balance >= self.amount_inc_tax:

                            self.collection_id.wallet_balance = self.collection_id.wallet_balance - self.amount_inc_tax
                            student.sudo().write({
                                'payment_ids': [
                                    (0, 0, {
                                        'sl_no': 1,
                                        'date': fields.Datetime.now(),
                                        'payment_mode': self.payment_mode,
                                        'fee_type': self.fee_type,  # Adjust field name if necessary
                                        'amount_exc_tax': self.amount_exc_tax,
                                        'amount_inc_tax': self.amount_inc_tax,
                                        'cheque_no': self.cheque_no,
                                        'branch': self.branch
                                    }),
                                ]
                            })
                            if self.fee_type == 'Batch Fee':
                                if self.collection_id.paid_amount == 0:
                                    self.collection_id.paid_amount = self.amount_inc_tax
                                else:
                                    self.collection_id.paid_amount = self.collection_id.paid_amount + self.amount_inc_tax
                        else:
                            raise ValidationError(_(
                                "Invalid Wallet Amount!"))
                    else:
                        if self.collection_id.wallet_balance >= self.amount_exc_tax:
                            self.collection_id.wallet_balance = self.collection_id.wallet_balance - self.amount_exc_tax
                            student.sudo().write({
                                'payment_ids': [
                                    (0, 0, {
                                        'sl_no': 1,
                                        'date': fields.Datetime.now(),
                                        'payment_mode': self.payment_mode,
                                        'fee_type': self.fee_type,  # Adjust field name if necessary
                                        'amount_exc_tax': self.amount_exc_tax,
                                        'amount_inc_tax': self.amount_inc_tax,
                                        'cheque_no': self.cheque_no,
                                        'branch': self.branch
                                    }),
                                ]
                            })
                            if self.fee_type == 'Batch Fee':
                                self.collection_id.paid_amount = self.collection_id.paid_amount + self.amount_exc_tax
                        else:
                            raise UserError('Invalid Wallet Amount.')
        else:
            student = self.env['op.student'].browse(self.collection_id.id)

            # Ensure the record exists and the `collection_id` is correctly set
            if student:
                student.sudo().write({
                    'payment_ids': [
                        (0, 0, {
                            'sl_no': 1,
                            'date': fields.Datetime.now(),
                            'payment_mode': self.payment_mode,
                            'fee_type': self.fee_type,  # Adjust field name if necessary
                            'amount_exc_tax': self.amount_exc_tax,
                            'amount_inc_tax': self.amount_inc_tax,
                            'cheque_no': self.cheque_no,
                            'branch': self.branch
                        }),
                    ]
                })
                if self.fee_type == 'Batch Fee':
                    self.collection_id.paid_amount = self.collection_id.paid_amount + self.amount_exc_tax

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
    payment_type = fields.Char(string="Payment Type")
    fee_type = fields.Char(string="Fee Type")
    invoice_no = fields.Char(string="Invoice No")
    reference_no = fields.Char(string="Reference No")
    amount_exc_tax = fields.Char(string="Amount (Exc. Tax)")
    amount_inc_tax = fields.Char(string="Amount (Inc. Tax)")
    payment_id = fields.Many2one('op.student', string="Payment")
    branch = fields.Selection(
        [('Corporate Office & City Campus', 'Corporate Office & City Campus'), ('Cochin Campus', 'Cochin Campus'),
         ('Calicut Campus', 'Calicut Campus'), ('Trivandrum Campus', 'Trivandrum Campus'),
         ('Kottayam Campus', 'Kottayam Campus'),
         ('Perinthalmanna Branch', 'Perinthalmanna Branch'), ('Bangalore Campus', 'Bangalore Campus')], string="Branch")
    cheque_no = fields.Char(string="Cheque No/Reference No")

