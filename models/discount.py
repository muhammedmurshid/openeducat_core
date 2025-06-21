from odoo import fields,models,api, _
from datetime import date

class Discount(models.Model):
   """This model is used for sending WhatsApp messages through Odoo."""
   _name = 'discount.request'
   _description = "Discount Requests"
   _inherit = ['mail.thread', 'mail.activity.mixin']
   _rec_name = "student_id"
   _order = "id desc"

   student_id = fields.Many2one('op.student', string="Student", required=1)
   request_date = fields.Date(string="Request Date", default=fields.Date.today)
   mobile = fields.Char(related='student_id.mobile', required=True)
   discount_scheme = fields.Selection([('special', 'Special'), ('scholarship','Scholarship')], string="Scheme", required=True)
   amount = fields.Float(string="Amount", required=1)
   reason = fields.Text(string="Reason", requied=1)
   approval_date = fields.Date(string="Approval Date")
   approved_by = fields.Many2one('res.users', string="Approved By")
   rejected_by = fields.Many2one('res.users', string="Rejected By")
   requested_by = fields.Many2one('res.users', string="Requested By")
   batch_id = fields.Many2one('op.batch', string="Batch", required=1)
   state = fields.Selection([('draft', 'Draft'), ('head_approval', 'Head Approval'), ('approved', 'Approved'), ('rejected', 'Rejected')], default='draft', string="Status", tracking=1)
   batch_ids = fields.Many2many('op.batch', string="Batches")

   def act_approve(self):
      self.approval_date = fields.Date.today()
      self.approved_by = self.env.user.id
      discount = self.env['discount.report'].sudo().create({
         'approved_date': fields.Datetime.now(),
         'amount': self.amount,
         'name': self.student_id.name,
         'student_id': self.student_id.id,
         'added_date': self.request_date,
         'discount_scheme': self.discount_scheme,
         'approved_by': self.env.user.id,
         'requested_by': self.requested_by.id,
         'batch_id': self.batch_id.id,
      })

      sl_no = len(self.student_id.payment_ids)

      last_record = self.env['discount.report'].sudo().search([], order='id desc', limit=1)
      self.student_id.payment_ids = [(0, 0, {'date': self.approval_date, 'payment_mode': 'Discount',
                                  'voucher_name': 'Gateway Receipt', 'sl_no': sl_no + 1,
                                  'credit_amount': self.amount, 'voucher_no': last_record,
                                  'type': 'discount', 'batch_name': self.student_id.batch_id.name,
                                  'course_name': self.student_id.course_id.name, 'fee_name': 'Discount'})]
      for enrollment in self.student_id.enrollment_ids:
         if enrollment.batch_id == self.batch_id:
            enrollment.discount += self.amount

      self.student_id.due_amount -= self.amount
      self.student_id.discount += self.amount
      self.state = 'approved'

   def act_reject(self):
      self.rejected_by = self.env.user.id
      self.state = 'rejected'

   def act_confirm_request(self):
      self.requested_by = self.env.user.id
      self.state = 'head_approval'
