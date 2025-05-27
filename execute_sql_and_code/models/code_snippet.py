from odoo import api, fields, models


class CodeSnippet(models.Model):
    _name = 'code.snippet'
    _description = 'Code Snippet'
    _order = 'name'

    name = fields.Char(string='Name', required=True, index=True)
    description = fields.Text(string='Description')
    snippet_type = fields.Selection([
        ('sql', 'SQL'),
        ('code', 'Python Code'),
        ('shell', 'Shell Command')
    ], string='Type', required=True, default='code')
    code = fields.Text(string='Code', required=True)
    is_favorite = fields.Boolean(string='Favorite', default=False)
    create_date = fields.Datetime(string='Created On', readonly=True)
    create_uid = fields.Many2one('res.users', string='Created By', readonly=True)

    def action_execute_snippet(self):
        """Execute the snippet directly from the list/form view"""
        self.ensure_one()
        wizard = self.env['sql.query.wizard'].create({
            'sql_or_code': self.snippet_type,
            'query': self.snippet_type == 'sql' and self.code or False,
            'code': self.snippet_type == 'code' and self.code or False,
            'shell_command': self.snippet_type == 'shell' and self.code or False,
        })

        return {
            'name': f'Execute: {self.name}',
            'type': 'ir.actions.act_window',
            'res_model': 'sql.query.wizard',
            'view_mode': 'form',
            'view_id': self.env.ref('execute_sql_and_code.view_sql_query_wizard').id,
            'res_id': wizard.id,
            'target': 'new',
        }

    def toggle_favorite(self):
        """Toggle the favorite status of the snippet"""
        for record in self:
            record.is_favorite = not record.is_favorite
        return True
