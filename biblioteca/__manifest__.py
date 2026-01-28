{
    'name': "Biblioteca",
    'summary': "Gestión de Libros con sus Autores",

    'description': 
        """
        Long description of module's purpose
        """,

    'author': "JOELTHEPRO",
    'website': "https://www.yourcompany.com",

    # Categories can be used to filter modules in modules listing
    # Check https://github.com/odoo/odoo/blob/15.0/odoo/addons/base/data/ir_module_category_data.xml
    # for the full list
    'category': 'Tools',
    'version': '1.0',
    
    # any module necessary for this one to work correctly
    'depends': ['base'],
    'data': [
        'security/ir.model.access.csv',
        'wizards/import_wizard_view.xml',
        'views/biblioteca_views.xml',
    ],
    
    'installable': True,
    'application': True,
    'license': 'LGPL-3',
}

