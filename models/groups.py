from odoo import fields, models, _, api

class LogicGroups(models.Model):
    _name = 'op.group'

    name = fields.Char(string="Name")
    code = fields.Char(string="Code")