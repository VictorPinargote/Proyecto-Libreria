from odoo import models, fields

class BibliotecaAutor(models.Model):
    _name = 'biblioteca.autor'
    _description = 'Autor'
    _rec_name = 'nombre'

    nombre = fields.Char(string="Nombre", required=True)
    apellido = fields.Char(string="Apellido")
    nacionalidad = fields.Char(string="Nacionalidad")