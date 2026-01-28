from odoo import models, fields

class BibliotecaLibro(models.Model):
    _name = 'biblioteca.libro'
    _description = 'Libro'
    _rec_name = 'titulo'

    isbn = fields.Char(string="ISBN", required=True)
    titulo = fields.Char(string="Título", required=True)
    autor_id = fields.Many2one('biblioteca.autor', string="Autor")
    
    # Datos traídos de la API
    portada = fields.Binary(string="Portada")
    descripcion = fields.Text(string="Descripción")
    editorial = fields.Char(string="Editorial")
    paginas = fields.Integer(string="Páginas")
    
    # Estado informativo simple
    estado = fields.Selection([
        ('disponible', 'Disponible'), 
        ('mantenimiento', 'Mantenimiento'), 
        ('perdido', 'Perdido')
    ], default='disponible', string="Estado")