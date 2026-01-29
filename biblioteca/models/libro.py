from odoo import models, fields, api
from odoo.exceptions import UserError
import requests

class BibliotecaLibro(models.Model):
    _name = 'biblioteca.libro'
    _description = 'Libro'
    _rec_name = 'titulo'

    # Campos de tu modelo actual
    isbn = fields.Char(string="ISBN", required=True)
    titulo = fields.Char(string="Título", required=True)
    autor_id = fields.Many2one('biblioteca.autor', string="Autor")
    paginas = fields.Integer(string="Páginas")
    editorial = fields.Char(string="Editorial")
    estado = fields.Selection([('disponible', 'Disponible')], default='disponible')
    portada = fields.Binary(string="Portada")

    def action_sincronizar_api(self):
        # URL y Token verificados
        url_api = 'http://localhost:8000/api/libros/' 
        token = '4af65a4e59810b00c011b906de3ee7703d28f432' 

        headers = {
            'Authorization': f'Token {token}',
            'Content-Type': 'application/json'
        }

        try:
            response = requests.get(url_api, headers=headers, timeout=10)
            
            if response.status_code == 200:
                libros_django = response.json()
                contador = 0
                
                for item in libros_django:
                    # Buscamos si ya existe por ISBN
                    existe = self.search([('isbn', '=', item.get('isbn'))], limit=1)
                    
                    if not existe:
                        # Gestionar Autor
                        autor_nombre = item.get('autor_nombre', 'Desconocido')
                        autor = self.env['biblioteca.autor'].search([('name', '=', autor_nombre)], limit=1)
                        if not autor:
                            autor = self.env['biblioteca.autor'].create({'name': autor_nombre})

                        # CREAR EL LIBRO (Usando 'titulo' correctamente)
                        self.create({
                            'titulo': item.get('titulo'), 
                            'isbn': item.get('isbn'),
                            'paginas': item.get('paginas', 0),
                            'editorial': item.get('editorial', ''),
                            'autor_id': autor.id,
                            'estado': 'disponible'
                        })
                        contador += 1
                
                return {
                    'type': 'ir.actions.client',
                    'tag': 'display_notification',
                    'params': {
                        'title': 'Sincronización OK',
                        'message': f'Se importaron {contador} libros nuevos.',
                        'type': 'success',
                    }
                }
            else:
                raise UserError(f"API Error: {response.status_code}")
        except Exception as e:
            raise UserError(f"Error: {str(e)}")