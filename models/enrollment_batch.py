from odoo import models, api, _, fields


class BatchEnrollmentWizard(models.TransientModel):
    _name = 'enrollment.batch.wizard'
    _description = 'Batch Enrollment'

    student_id = fields.Many2one('op.student', string='Student', required=1)
    batch_id = fields.Many2one('op.batch', string="Batch", required=1)
    course_id = fields.Many2one('op.course', string="Course", related="batch_id.course_id")
    fee_type = fields.Selection([('lump_sum_fee', 'Lump Sum Fee'), ('installment', 'Installment')], string='Fee Type',
                                required=1)
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
        for record in self:
            if not record.student_id:
                raise ValueError("No student specified for enrollment.")
            if not record.batch_id:
                raise ValueError("No batch specified for enrollment.")
            # Capture old batch details before changing
            old_batch = record.student_id.batch_id
            old_fee_type = record.student_id.fee_type
            old_course = record.student_id.course_id
            old_start_date = record.student_id.batch_start_date
            old_end_date = record.student_id.batch_end_date
            old_admission_date = record.student_id.admission_date
            old_payable_fee = record.student_id.total_payable_tax
            old_due_amount = record.student_id.due_amount

            # Remove student from old batch
            # old_batch.sudo().write({'student_ids': [(3, record.student_id.id)]})

            # Update student batch
            if self.batch_id.add_on_batch == 1:
                record.student_id.sudo().write({
                    'batch_id': old_batch.id
                })
            else:
                record.student_id.sudo().write({
                    'batch_id': record.batch_id.id
                })

            # Add enrollment records
            if record.student_id.enrolled == 1:
                record.student_id.sudo().write({
                    'enrollment_ids': [
                        (0, 0, {
                            'batch_id': record.batch_id.id,
                            'fee_type': record.fee_type,
                            'course_id': record.course_id.id,
                            'batch_fee': record.batch_fee,
                            'start_date': record.start_date,
                            'end_date': record.end_date,
                            'total_payable': record.batch_fee,
                            'enrolled_date': record.enrollment_date,
                            'due_amount': record.batch_fee,
                        }),
                    ]
                })
            else:
                # Add old batch enrollment first
                record.student_id.sudo().write({
                    'enrollment_ids': [
                        (0, 0, {
                            'batch_id': old_batch.id,
                            'fee_type': old_fee_type,
                            'course_id': old_course.id,
                            'start_date': old_start_date,
                            'end_date': old_end_date,
                            'total_payable': old_payable_fee,
                            'enrolled_date': old_admission_date,
                            'due_amount': old_due_amount,
                        }),
                        (0, 0, {
                            'batch_id': record.batch_id.id,
                            'fee_type': record.fee_type,
                            'course_id': record.course_id.id,
                            'batch_fee': record.batch_fee,
                            'start_date': record.start_date,
                            'end_date': record.end_date,
                            'total_payable': record.batch_fee,
                            'enrolled_date': record.enrollment_date,
                            'due_amount': record.batch_fee,
                        }),
                    ]
                })

        student = self.student_id
        student.enrolled = True
        student.due_amount += self.batch_fee
        # student.batch_id = self.batch_id.id
        student.fee_type = self.fee_type
        student.branch_id = self.branch_id.id
        student.admission_date = self.enrollment_date
        # student.message_post(body=msg)
