from odoo import models, api, _, fields

class BatchEnrollmentWizard(models.TransientModel):
    _name = 'enrollment.batch.wizard'
    _description = 'Batch Enrollment'

    student_id = fields.Many2one('op.student', string='Student', required=1)
    batch_id = fields.Many2one('op.batch', string="Batch", required=1)
    course_id = fields.Many2one('op.course', string="Course", related="batch_id.course_id")
    fee_type = fields.Selection([('lump_sum_fee', 'Lump Sum Fee'), ('installment','Installment')], string='Fee Type', required=1)
    batch_fee = fields.Float(string="Batch Fee", compute="_compute_batch_fee", store=1)
    start_date = fields.Date(string="Start Date", related="batch_id.start_date")
    end_date = fields.Date(string="End Date", related="batch_id.end_date")
    enrollment_date = fields.Date(string="Enrollment Date", default=fields.Datetime.now)


    @api.onchange('batch_id')
    def _onchange_branch(self):
        if self.batch_id:
            print(self.batch_id.branch, 'ooops')
            self.branch_id = self.batch_id.branch.id

    @api.depends('fee_type')
    def _compute_batch_fee(self):
        for i in self:
            if i.batch_id:
                if i.fee_type == 'lump_sum_fee':
                    i.batch_fee = i.batch_id.total_lump_sum_fee
                if i.fee_type == 'installment':
                    i.batch_fee = i.batch_id.total_installment_fee

    def enrollment_batch(self):
        old_batch = self.student_id.batch_id
        old_batch.sudo().write({'student_ids': [(3, self.student_id.id)]})
        for record in self:  # Iterate over each enrollment_batch record

            if not record.student_id:
                raise ValueError("No student specified for enrollment.")
            if not record.batch_id:
                raise ValueError("No batch specified for enrollment.")

            # Update student batch using write
            record.student_id.sudo().write({
                'batch_id': record.batch_id.id
            })
        print(self.batch_id, 'batch')
        # self.batch_id.sudo().write({
        #     'student_ids': [(0, 0, {'student_name': self.student_id.id, 'mobile': self.student_id.mobile, 'date_of_admission': self.enrollment_date})]
        # })
        if self.student_id.enrolled == 1:
            self.student_id.sudo().write({
                'enrollment_ids': [
                    (0, 0, {'batch_id': self.batch_id.id, 'fee_type': self.fee_type, 'course_id': self.course_id.id,
                            'batch_fee': self.batch_fee, 'start_date': self.start_date, 'end_date': self.end_date, 'enrolled_date': self.enrollment_date
                            }),

                    # Add valid data
                ]
            })

        else:
            print('naa')
            self.student_id.sudo().write({
                'enrollment_ids': [
                    (0, 0, {
                        'batch_id': self.student_id.batch_id.id,
                        'fee_type': self.student_id.fee_type,
                        'course_id': self.student_id.course_id.id,
                        'start_date': self.student_id.batch_start_date,
                        'end_date': self.student_id.batch_end_date,
                        'enrolled_date': self.student_id.admission_date,

                    }),
                    (0, 0, {'batch_id': self.batch_id.id, 'fee_type': self.fee_type, 'course_id': self.course_id.id,
                            'batch_fee': self.batch_fee, 'start_date': self.start_date, 'end_date': self.end_date, 'enrolled_date': self.enrollment_date
                            }),

                    # Add valid data
                ]
            })

        student = self.student_id
        student.enrolled = True
        student.due_amount += self.batch_fee
        # student.batch_id = self.batch_id.id
        student.fee_type = self.fee_type
        student.admission_date = self.enrollment_date
            # student.message_post(body=msg)