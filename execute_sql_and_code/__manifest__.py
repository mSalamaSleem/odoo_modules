{
    'name': "Sql Query or Code Execution",
    'summary': """
        This module allows users to execute SQL queries or Python code in Odoo.""",
    'description': """
        This module allows users to execute SQL queries or Python code in Odoo.
    """,
    'author': "Mahmoud Salama",
    'website': "https://www.linkedin.com/in/mahmoud-salama-36a6a1164",
    'category': 'Development Tools',
    'version': '0.1',
    'depends': ['base'],
    'data': [
        'security/ir.model.access.csv',
        'wizard/sql_query_wizard_view.xml',
    ],
    'images': ['static/description/assets/images.gif'],
    'license': 'LGPL-3',
    'application': True,
    'sequence': -100
}
