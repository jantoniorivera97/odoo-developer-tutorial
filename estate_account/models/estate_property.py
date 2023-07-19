from odoo import models

class EstateProperty(models.Model):
    _inherit = "estate.property"

    def action_sold(self):
        move_id = self.env["account.move"].create(
            {
                "move_type": "out_invoice",
                "partner_id": self.partner_id.id,
            })

        invoice_line = [
            {
                "name": "Selling Price Fee",
                "quantity": 1,
                "price_unit": self.selling_price * 0.06,
                'move_id': move_id.id,
                "journal_id": 4
            },
            {
                "name": "Administrative Fee",
                "quantity": 1,
                "price_unit": 100.00,
                'move_id': move_id.id,
                "journal_id": 4
            }
        ]
        self.env['account.move.line'].create(invoice_line)
        self.invoice_id = move_id.id

        return super().action_sold()
