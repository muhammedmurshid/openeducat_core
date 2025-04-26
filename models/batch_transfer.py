from odoo import fields,models,api,_

class BatchTransfer(models.TransientModel):
    _name = 'batch.transfer'
    _description = "Batch Transfer"

    student_id = fields.Many2one('op.student', string='Student', required=1, tracking=True)
    batch_id = fields.Many2one('op.batch', string="Batch", required=1, tracking=True)
    course_id = fields.Many2one('op.course', string="Course", related="batch_id.course_id")
    fee_type = fields.Selection([('lump_sum_fee', 'Lump Sum Fee'), ('installment', 'Installment')], string='Fee Type',
                                required=1, )


    def act_confirm(self):
        self.student_id.batch_id = self.batch_id.id
        self.student_id.course_id = self.course_id.id
        self.student_id.fee_type = self.fee_type
        self.student_id.due_amount = self.student_id.total_payable_tax - self.student_id.paid_amount