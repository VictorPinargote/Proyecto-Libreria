from odoo import models, fields

class BibliotecaLibro(models.Model):
    _name = 'biblioteca.libro'
    _description = 'Libro'
    _rec_name = 'titulo'

    # Estos nombres deben coincidir con lo que manda Django
    isbn = fields.Char(string="ISBN", required=True)
    titulo = fields.Char(string="Título", required=True)
    autor_id = fields.Many2one('biblioteca.autor', string="Autor")
    paginas = fields.Integer(string="Páginas")
    editorial = fields.Char(string="Editorial")
    estado = fields.Selection([('disponible', 'Disponible')], default='disponible')
    
    # Opcional: Si quieres ver la portada en Odoo (Django no la manda por defecto en este código simple, pero dejalo por si acaso)
    portada = fields.Binary(string="Portada")