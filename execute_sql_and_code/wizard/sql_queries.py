import json
import sys
import traceback
from io import StringIO

from odoo import api, fields, models, Command
from odoo.exceptions import UserError, AccessError


class SqlQueryWizard(models.TransientModel):
    _name = 'sql.query.wizard'
    _description = 'SQL Query Wizard'

    query = fields.Text(string='SQL Query')
    code = fields.Text(string='Code')
    code_result = fields.Html(string='Result', readonly=True)
    sql_result = fields.Html(string='Result', readonly=True)
    shell_command = fields.Text(string='Shell Command')
    shell_result = fields.Html(string='Shell Result', readonly=True)
    domain = fields.Char(string='Domain')
    model = fields.Many2one('ir.model', string='Model')
    domain_result = fields.Html(string='Result', readonly=True)
    sql_or_code = fields.Selection([
        ('sql', 'SQL'),
        ('code', 'Code'),
        ('file', 'File'),
        ('shell', 'Shell'),
        ('domain_sql', 'Domain to Sql')
    ], default='code')
    filename = fields.Char(string='File Name')
    file = fields.Binary(string='File')
    example1 = fields.Char(string='Examples', default='print(self)')
    example2 = fields.Char(string='Examples', default='print(context)')
    example3 = fields.Char(string='Examples', default="Command")

    code_examples = fields.Html(compute='_compute_code_examples')

    # Fields for saving snippets
    save_snippet = fields.Boolean(string='Save as Snippet')
    snippet_name = fields.Char(string='Snippet Name')
    snippet_description = fields.Text(string='Description')

    # Field for loading snippets
    snippet_id = fields.Many2one('code.snippet', string='Load Snippet')

    @api.depends('sql_or_code')
    def _compute_code_examples(self):
        examples = {
            'sql': [
                "SELECT name, email FROM res_partner LIMIT 10",
                "SELECT COUNT(*) FROM sale_order WHERE state = 'done'"
            ],
            'code': [
                "result = env['res.partner'].search_count([])",
                "result = [rec.name for rec in env['crm.lead'].search([])]"
            ],
            "shell": [
                "new_partner = res_partner.create({'name': 'Test Partner'})<br/>print(new_partner)",
                "for user in res_users.search([])[:5]:<br/>&emsp;print(user.name, user.email)"
            ],
            'domain_sql': [
                "Crm Lead",
                "[('type', '=', 'lead')]"
            ]
        }
        for record in self:
            lines = examples.get(record.sql_or_code, [])
            record.code_examples = f"<ol>{''.join([f'<li>{line}</li>' for line in lines])}</ol>"

    # @api.depends('sql_or_code', 'code')
    # def _compute_examples(self):
    #     my_list = '''
    #         <ol>
    #             <li><span class="text-danger">self: </span>view data of record</li>
    #             <li><span class="text-danger">self.env: </span>view data of environment</li>
    #             <li><span class="text-danger">result = []
    #                                           for rec in self.env['crm.lead'].search([]):
    #                                               result.append(rec.name)
    #                                         :</span>loop on records</li>
    #         </or>
    #     '''
    #     if not self.code and self.sql_or_code == 'code':
    #         self.examples = my_list
    #     else:
    #         self.examples = ''

    def execute(self):
        if not self.env.user.has_group('base.group_system'):
            raise AccessError("Only system administrators can execute code")
        if self.sql_or_code == 'sql':
            return self.execute_sql()
        if self.sql_or_code == 'code':
            return self.execute_code()
        if self.sql_or_code == 'file':
            return self.execute_file()
        if self.sql_or_code == 'shell':
            return self.execute_shell()
        if self.sql_or_code == 'domain_sql':
            return self.execute_domain_to_sql()

    def execute_sql(self):
        if not self.query:
            raise UserError('Please enter a SQL query.')
        try:
            self.env.cr.execute(self.query)
            result = self.env.cr.fetchall()
            headers = [desc[0] for desc in self.env.cr.description]
            rows = [dict(zip(headers, row)) for row in result]

            # solution 1
            # table = '''
            #     <table class="table table-striped">
            #         <thead>
            #             <tr>{}</tr>
            #         </thead>
            #         <tbody>{}</tbody>
            #     </table>'''
            # self.result = table.format(
            #     ''.join(['<th>{}</th>'.format(h) for h in headers]),
            #     ''.join(['<tr>{}</tr>'.format(
            #         ''.join(['<td>{}</td>'.format(row.get(h, '')) for h in headers])) for row in rows])
            # )

            # solution 2
            table2 = f'''
                <table class="table table-striped table-responsive table-hover">
                    <thead class="thead-dark">
                        <tr>{''.join([f'<th>{h}</th>' for h in headers])}</tr>
                    </thead>
                    <tbody>
                        {''.join([f'<tr>{"".join([f"<td>{row.get(h)}</td>" for h in headers])}</tr>' for row in rows])}
                    </tbody>
                </table>
            '''

            self.sql_result = table2
        except Exception as e:
            raise UserError('Failed to execute the SQL query: {}'.format(e))

        # Save snippet if requested
        if self.save_snippet and self.snippet_name:
            self._save_as_snippet()

        return self.action_wizard_form()

    def execute_code(self):
        self.ensure_one()
        if not self.code:
            raise UserError('Please enter Python code.')
        try:
            # Create a more comprehensive local execution context
            local_context = {
                'self': self,
                'context': self.env.context,
                'Command': Command,  # Add Command for ORM operations
                'result': [],  # Predefined result list
            }

            # Modify code execution to handle different code structures
            code_to_execute = self.code.strip()

            # If the code doesn't start with 'result =', assume it's a block of code that should populate result
            if not code_to_execute.startswith('result ='):
                code_to_execute = f"""{code_to_execute}
                    """
            # Execute the code with the expanded context
            exec(code_to_execute, globals(), local_context)

            # Convert result to list if it's not already a list
            result = local_context.get('result', [])
            if not isinstance(result, list):
                result = [result]
            # Format the result for HTML display
            self.code_result = '<ol>' + ''.join([f'<li>{str(item)}</li>' for item in result]) + '</ol>'

        except Exception as e:
            # Improved error handling with more context
            import traceback
            error_trace = traceback.format_exc()
            raise UserError(f'Failed to execute the Python code: {e}\n\nDetailed Traceback:\n{error_trace}')

        # Save snippet if requested
        if self.save_snippet and self.snippet_name:
            self._save_as_snippet()

        return self.action_wizard_form()

    def execute_file(self):
        self.ensure_one()
        if not self.file:
            raise UserError('Please select a file to execute.')
        import base64

        try:
            local_context = {
                'self': self,
                'context': self.env.context,
                'Command': Command,  # Add Command for ORM operations
                'result': [],  # Predefined result list
            }
            decoded_contents = base64.b64decode(self.file).decode('utf-8')
            code_to_execute = decoded_contents.strip()
            if not decoded_contents.startswith('result ='):
                code_to_execute = f"""{code_to_execute}
                    """
            exec(code_to_execute, globals(), local_context)

            result = local_context.get('result', [])
            if not isinstance(result, list):
                result = [result]

            self.code_result = '<ol>' + ''.join([f'<li>{str(item)}</li>' for item in result]) + '</ol>'

        except Exception as e:
            import traceback
            error_trace = traceback.format_exc()
            raise UserError(f'Failed to execute the Python code: {e}\n\nDetailed Traceback:\n{error_trace}')

        # Save snippet if requested
        if self.save_snippet and self.snippet_name:
            self._save_as_snippet()

        return self.action_wizard_form()

    def execute_shell(self):
        """
        Attempt to create an Odoo shell-like environment
        """
        # Capture stdout
        old_stdout = sys.stdout
        sys.stdout = captured_output = StringIO()

        try:
            local_namespace = {
                'self': self,
                'env': self.env,
                'cr': self.env.cr,
                'uid': self._uid,
                'context': self._context,
                'Command': Command,
            }

            for model_name in self.env.registry.models:
                safe_attr_name = model_name.replace('.', '_')
                local_namespace[safe_attr_name] = self.env[model_name]
            try:
                compiled_code = compile(self.shell_command, '<string>', 'exec')
                exec(compiled_code, local_namespace)
            except Exception as e:
                print(f"Error executing shell command: {e}")
                traceback.print_exc()

            # Restore stdout and get the output
            sys.stdout = old_stdout
            output = captured_output.getvalue()

            # Store the result
            self.shell_result = f'<pre>{output}</pre>'

        except Exception as final_error:
            # Restore stdout
            sys.stdout = old_stdout

            error_trace = traceback.format_exc()
            self.shell_result = f'<pre>Shell execution failed: {final_error}\n{error_trace}</pre>'

        # Save snippet if requested
        if self.save_snippet and self.snippet_name:
            self._save_as_snippet()

        return self.action_wizard_form()

    def execute_domain_to_sql(self):
        if not self.domain or not self.model:
            raise UserError('Please enter a domain and select a model.')

        domain = self.get_domain()
        try:
            query = self.env[self.model.model]._where_calc(domain)
            code = query.select().code
            params = query.select().params
            query_with_params = code.replace('%s', '%r') % tuple(params)

            self.domain_result = f'<pre>{query_with_params};</pre>'

        except Exception as e:
            raise UserError('Failed to convert domain: {}'.format(e))

        return self.action_wizard_form()

    def get_domain(self):
        domain = self.check_domain_syntax()
        return eval(domain)

    def check_domain_syntax(self):
        domain = self.domain.strip()
        if not domain.startswith('['):
            domain = f"[{domain}"
        if not domain.endswith(']'):
            domain = f"{domain}]"
        return domain

    def action_wizard_form(self):
        return {
            'type': 'ir.actions.act_window',
            'res_model': 'sql.query.wizard',
            'view_mode': 'form',
            'view_id': self.env.ref('execute_sql_and_code.view_sql_query_wizard').id,
            'res_id': self.id,
            'target': 'new',
        }

    def _save_as_snippet(self):
        """Save the current code as a snippet"""
        if not self.snippet_name:
            raise UserError('Please provide a name for the snippet.')

        code_content = ''
        snippet_type = self.sql_or_code

        if snippet_type == 'sql':
            code_content = self.query
        elif snippet_type == 'code':
            code_content = self.code
        elif snippet_type == 'shell':
            code_content = self.shell_command
        else:
            return

        if not code_content:
            raise UserError('No code content to save.')

        self.env['code.snippet'].create({
            'name': self.snippet_name,
            'description': self.snippet_description or '',
            'snippet_type': snippet_type,
            'code': code_content,
        })

        return {'type': 'ir.actions.client', 'tag': 'display_notification', 'params': {
            'title': 'Success',
            'message': f'Snippet "{self.snippet_name}" saved successfully',
            'type': 'success',
            'sticky': False,
        }}

    @api.onchange('snippet_id')
    def _onchange_snippet_id(self):
        """Load the selected snippet"""
        if self.snippet_id:
            self.sql_or_code = self.snippet_id.snippet_type

            if self.snippet_id.snippet_type == 'sql':
                self.query = self.snippet_id.code
            elif self.snippet_id.snippet_type == 'code':
                self.code = self.snippet_id.code
            elif self.snippet_id.snippet_type == 'shell':
                self.shell_command = self.snippet_id.code
