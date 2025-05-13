from odoo import fields, models, api, _


class BillCancellation(models.TransientModel):
    _name = 'bill.cancellation'
    _description = 'Bill Cancellation'

    clarification = fields.Text(
        default="Are you sure you want to cancel this bill? This action is irreversible and may affect related financial records. Please confirm only if you are certain")
    accepted = fields.Boolean(string="Accepted")
    payment_id = fields.Many2one('fee.payment.history')
    reason = fields.Text(string="Cancellation Reason")

    def action_cancel_bill(self):
        print('hi')
        invoice = self.env['invoice.reports'].sudo().search(
            [('invoice_number', '=', self.payment_id.voucher_no), ('invoice_number', '!=', '')])
        receipt = self.env['receipts.report'].sudo().search(
            [('receipt_no', '=', self.payment_id.voucher_no), ('receipt_no', '!=', '')])
        print(invoice.name, 'invoice')
        print(receipt.name, 'receipt')
        self.payment_id.state = 'cancelled'
        invoice.state = 'cancelled'
        receipt.state = 'cancelled'
        self.payment_id.cancellation_reason = self.reason
        if self.payment_id.voucher_name == 'Opening Balance':
            self.payment_id.payment_id.due_amount -= self.payment_id.debit_amount
        if self.payment_id.type == 'invoice':
            if self.payment_id.fee_name != 'Admission Fee':
                self.payment_id.payment_id.due_amount += self.payment_id.debit_amount
        if self.payment_id.type == 'receipt':
            self.payment_id.payment_id.wallet_balance -= self.payment_id.credit_amount