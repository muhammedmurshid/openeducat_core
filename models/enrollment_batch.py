from odoo import models, api, _, fields

class BatchEnrollmentWizard(models.TransientModel):
    _name = 'enrollment.batch.wizard'
    _description = 'Batch Enrollment'

    student_id = fields.Many2one('op.student', string='Student')
