from odoo import fields, models, api, _

class DropStudentProfileWizard(models.TransientModel):
    _name = 'drop.student.wizard'

    student_id = fields.Many2one('op.student', string="Student")
    drop_date = fields.Date(string="Drop Date", required=1)
    reason = fields.Text(string="Reason", requiired=1)

    def act_submit_drop(self):
        if self.student_id:
            self.student_id.drop_date = self.drop_date
            self.student_id.drop_reason = self.reason
            self.student_id.state = 'stoped'