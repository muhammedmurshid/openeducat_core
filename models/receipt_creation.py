from odoo import fields, models, api, _
from num2words import num2words


class CreateReceiptWizard(models.TransientModel):
    """This model is used for sending WhatsApp messages through Odoo."""
    _name = 'create.receipt.wizard'
    _description = "Receipt Wizard"

    remarks = fields.Text(string="Remarks")
    date = fields.Date(string="Date", required=1)
    student_id = fields.Many2one('op.student', string="Student")
    student_name = fields.Char(string="Name")
    cheque_no = fields.Char(string="Cheque No/Reference No")
    amount = fields.Float(string="Amount")
    admission_officer = fields.Boolean(string='Admission Officer')
    payment_mode = fields.Selection([('Cash', 'Cash'), ('Bank Direct', 'Bank Direct'), ('Gateway', 'Gateway')], default='Cash', string="Payment Mode")
    reference_no = fields.Char(string="Reference No.")

    # batch_id = fields.Many2one(string="Batch")
    # branch_id = fields.Many2one(string="Branch")
    branch = fields.Selection(
        [('Corporate Office & City Campus', 'Corporate Office & City Campus'), ('Cochin Campus', 'Cochin Campus'),
         ('Calicut Campus', 'Calicut Campus'), ('Trivandrum Campus', 'Trivandrum Campus'),
         ('Kottayam Campus', 'Kottayam Campus'),
         ('Perinthalmanna Branch', 'Perinthalmanna Branch'), ('Bangalore Campus', 'Bangalore Campus')], string="Branch")
    collected_by = fields.Many2one('res.users', default=lambda self: self.env.user.id)

    amount_in_words = fields.Char(string="Amount in Words", compute="_compute_amount_in_words", store=1)
    batch_id = fields.Many2one('op.batch', string="Batch")

    @api.depends('amount')
    def _compute_amount_in_words(self):
        print('workssssss')
        for i in self:
            i.amount_in_words = num2words(i.amount, lang='en').upper()

    @api.onchange('admission_officer')
    def _onchange_admission_officer(self):
        if self.admission_officer == 1:
            self.payment_mode = 'Cash'

    def act_submit(self):
        print('hh', self.payment_mode)
        if self.student_id:
            self.student_id.wallet_balance += self.amount
        receipt = self.env['receipts.report'].sudo().create({
            'date': self.date,
            'amount': self.amount,
            'name': self.student_name,
            'branch': self.branch,
            'payment_mode': self.payment_mode,
            'student_id': self.student_id.id,
            'batch': self.batch_id.name,
            'reference_no': self.reference_no,
            'fee_collector_id': self.env.user.id,
            'batch_id': self.batch_id.id

        })
        voucher = self.env['receipts.report'].sudo().search([], order="id desc", limit=1)
        for rec in self:
            # last_payment = self.env['fee.payment.history'].sudo().search(
            #     [('student_id', '=', rec.student_id.id)], order="sl_no desc", limit=1
            # )
            # new_sl_no = last_payment.sl_no + 1 if last_payment else 1
            sl_no = len(rec.student_id.payment_ids)

            voucher_name = 'Receipt'
            if rec.payment_mode == 'Cash':
                voucher_name = 'Cash Receipt'
            elif rec.payment_mode == 'Gateway':
                voucher_name = 'Gateway Receipt'
            elif rec.payment_mode == 'bank':
                voucher_name = 'Bank Direct'
            # Add new payment entry
            rec.student_id.payment_ids = [(0, 0, {
                'sl_no': sl_no + 1,
                'date': rec.date,
                'voucher_name': voucher_name,
                'payment_mode': rec.payment_mode,
                'voucher_no': receipt.receipt_no if receipt else 'INV-000',
                'reference_no': voucher.receipt_no if voucher else 'N/A',
                'amount_exc_tax': 0,
                'amount_inc_tax': 0,
                'type': 'receipt',
                'fee_name': 'Receipt',
                'debit_amount': 0,
                'credit_amount': rec.amount,
                'branch': self.branch

            })]

    @api.onchange('student_id')
    def _onchange_student_name(self):
        if self.student_id:
            self.student_name = self.student_id.name