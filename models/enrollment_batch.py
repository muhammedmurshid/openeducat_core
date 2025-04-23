from odoo import models, api, _, fields

class BatchEnrollmentWizard(models.TransientModel):
    _name = 'enrollment.batch.wizard'
    _description = 'Batch Enrollment'

    student_id = fields.Many2one('op.student', string='Student', required=1)
    batch_id = fields.Many2one('op.batch', string="Batch", required=1)
    fee_type = fields.Selection([('lump_sum_fee', 'Lump Sum Fee'), ('installment','Installment')], string='Fee Type', required=1)

    def enrollment_batch(self):
        print('hi')
        self.student_id.enrolled = True
