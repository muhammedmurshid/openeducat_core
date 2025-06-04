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
        old_batch = self.student_id.batch_id

        # Update student's fields
        self.student_id.batch_id = self.batch_id.id
        self.student_id.course_id = self.course_id.id
        self.student_id.fee_type = self.fee_type
        self.student_id.due_amount = self.student_id.total_payable_tax - self.student_id.paid_amount

        new_batch = self.batch_id

        if old_batch and old_batch != new_batch:
            # Remove student from old batch
            student_to_remove = old_batch.student_ids.filtered(lambda s: s.student_name.id == self.student_id.id)
            if student_to_remove:
                student_to_remove = student_to_remove[0] if len(student_to_remove) > 1 else student_to_remove
                old_batch.sudo().write({'student_ids': [(3, student_to_remove.id)]})
                old_batch.total_no_of_students -= 1

            # Add student to new batch
            existing_student = new_batch.student_ids.filtered(lambda s: s.student_name.id == self.student_id.id)
            if not existing_student:
                new_batch.sudo().write({
                    'student_ids': [(0, 0, {
                        'student_id': self.student_id.id,
                        'student_name': self.student_id.id,
                        'mobile': self.student_id.mobile,
                        'date_of_admission': self.student_id.admission_date,
                    })]
                })
                new_batch.total_no_of_students += 1
