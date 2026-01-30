from odoo import models, fields

class BibliotecaAutor(models.Model):
    _name = 'biblioteca.autor'
    _description = 'Autor del Libro'
    _rec_name = 'nombre'

    nombre = fields.Char(string="Nombre", required=True)
    bibliografia = fields.Text(string="Bibliografía")

    _sql_constraints = [
        ('name_uniq', 'unique (nombre)', 'El nombre del autor debe ser único.')
    ]
