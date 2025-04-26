from odoo import models, api, _, fields

class BatchEnrollmentWizard(models.TransientModel):
    _name = 'enrollment.batch.wizard'
    _description = 'Batch Enrollment'

    student_id = fields.Many2one('op.student', string='Student', required=1)
    batch_id = fields.Many2one('op.batch', string="Batch", required=1)
    course_id = fields.Many2one('op.course', string="Course", related="batch_id.course_id")
    fee_type = fields.Selection([('lump_sum_fee', 'Lump Sum Fee'), ('installment','Installment')], string='Fee Type', required=1)
    batch_fee = fields.Float(string="Batch Fee", compute="_compute_batch_fee", store=1)

    @api.depends('fee_type')
    def _compute_batch_fee(self):
        for i in self:
            if i.batch_id:
                if i.fee_type == 'lump_sum_fee':
                    i.batch_fee = i.batch_id.total_lump_sum_fee
                if i.fee_type == 'installment':
                    i.batch_fee = i.batch_id.total_installment_fee

    def enrollment_batch(self):
        print('hi')

        self.batch_id.sudo().write({
            'student_ids': [(0, 0, {'student_name': self.student_id.id, 'mobile': self.student_id.mobile, 'date_of_admission': self.student_id.admission_date})]
        })
        if self.student_id.enrolled == 1:
            self.student_id.sudo().write({
                'enrollment_ids': [
                    (0, 0, {'batch_id': self.batch_id.id, 'fee_type': self.fee_type, 'course_id': self.course_id.id,
                            'batch_fee': self.batch_fee
                            }),

                    # Add valid data
                ]
            })
            print('ya')

        else:
            print('naa')
            self.student_id.sudo().write({
                'enrollment_ids': [
                    (0, 0, {
                        'batch_id': self.student_id.batch_id.id,
                        'fee_type': self.student_id.fee_type,
                        'course_id': self.student_id.course_id.id,

                    }),
                    (0, 0, {'batch_id': self.batch_id.id, 'fee_type': self.fee_type, 'course_id': self.course_id.id,
                            'batch_fee': self.batch_fee
                            }),

                    # Add valid data
                ]
            })

        self.student_id.enrolled = True
        self.student_id.due_amount += self.batch_fee