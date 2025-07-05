from odoo import fields, models, api

class FeePlanChangingWizard(models.TransientModel):
   _name = 'change.payment.plan'
   _description = "Payment Wizard"

   student_id = fields.Many2one('op.student', string="Student")
   fee_type = fields.Selection(
       [('lump_sum_fee', 'Lump Sum Fee'), ('installment', 'Installment'), ('bajaj_finance_payment_plan','Bajaj Finance Payment Plan')], string="Fee Type")
   batch_id = fields.Many2one('op.batch', string="Batch")
   total_amount = fields.Float(string="Total Amount")

   @api.onchange('fee_type')
   def _onchange_fee_type(self):
      if self.fee_type:
         if self.fee_type == 'installment':
            self.total_amount = self.batch_id.total_installment_fee
         elif self.fee_type == 'lump_sum_fee':
            self.total_amount = self.batch_id.total_lump_sum_fee
         elif self.fee_type == 'bajaj_finance_payment_plan':
            self.total_amount = self.batch_id.bajaj_emi_total

   def act_change_fee_type(self):
      if self.fee_type:
         self.student_id.fee_type = self.fee_type
         if self.fee_type == 'lump_sum_fee':
            self.student_id.due_amount = self.batch_id.total_lump_sum_fee - self.student_id.paid_amount
         if self.fee_type == 'installment':
            self.student_id.due_amount = self.batch_id.total_installment_fee - self.student_id.paid_amount
         if self.fee_type == 'bajaj_finance_payment_plan':
            self.student_id.due_amount = self.batch_id.bajaj_emi_total - self.student_id.paid_amount
