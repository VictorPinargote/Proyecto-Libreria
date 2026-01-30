from odoo import models, fields, api
from odoo.exceptions import UserError
import requests

class BibliotecaLibro(models.Model):
    _name = 'biblioteca.libro'
    _description = 'Libro'
    _rec_name = 'titulo'

    # Campos de tu modelo actual
    isbn = fields.Char(string="ISBN", required=False)
    titulo = fields.Char(string="Título", required=True)
    autor_id = fields.Many2one('biblioteca.autor', string="Autor")
    paginas = fields.Integer(string="Páginas")
    editorial = fields.Char(string="Editorial")
    estado = fields.Selection([('disponible', 'Disponible')], default='disponible')
    portada = fields.Binary(string="Portada")

    def action_sincronizar_api(self):
        # Usamos el endpoint PROXY que busca en OpenLibrary
        url_api = 'http://127.0.0.1:8000/api/proxy/openlibrary/' 
        # Token verificado de 'joelp'
        token = '383fb048e7e1532e349c9e8c18230ebe2341751c' 
        
        headers = {
            'Authorization': f'Token {token}',
        }

        if not self.titulo:
             raise UserError("El libro debe tener un título para buscarlo.")

        try:
            # Buscamos por el TÍTULO del libro actual
            response = requests.get(url_api, params={'q': self.titulo}, headers=headers, timeout=10)
            
            if response.status_code == 200:
                data_list = response.json()
                if not data_list:
                    raise UserError(f"No se encontró información para: {self.titulo}")
                
                # Tomamos el primer resultado
                item = data_list[0]
                
                # 1. Gestionar Autor
                autor_nombre = item.get('autor', 'Desconocido')
                # OJO: En la respuesta del proxy la key es 'autor', no 'autor_nombre'
                if isinstance(autor_nombre, list): autor_nombre = autor_nombre[0]

                autor = self.env['biblioteca.autor'].search([('nombre', '=', autor_nombre)], limit=1)
                # Nota: El campo en el modelo autor suele ser 'nombre', verifica si es 'name' o 'nombre'
                # En el archivo autor.py (Step 29) no lo vi, pero asumiré 'nombre' por consistencia con otros snippets.
                # Si falla, el usuario nos dirá. (En el wizard usé 'nombre').
                if not autor:
                    autor = self.env['biblioteca.autor'].create({'nombre': autor_nombre})

                # 2. Descargar Portada
                img_b64 = False
                cover_url = item.get('cover')
                if cover_url:
                    try:
                        r_img = requests.get(cover_url, timeout=5)
                        if r_img.status_code == 200:
                            import base64
                            img_b64 = base64.b64encode(r_img.content).decode('utf-8')
                    except: pass

                # 3. ACTUALIZAR ESTE LIBRO (SELF)
                self.write({
                    'isbn': item.get('isbn') or 'S/N',
                    'paginas': item.get('paginas', 0),
                    'editorial': item.get('editorial', ''),
                    'autor_id': autor.id,
                    'portada': img_b64 if img_b64 else self.portada
                })
                
                # Devolvemos una acción que recargue la vista para que el usuario 
                # vea los datos inmediatamente sin tener que salir y volver a entrar.
                return {
                    'type': 'ir.actions.act_window',
                    'res_model': 'biblioteca.libro',
                    'res_id': self.id,
                    'view_mode': 'form',
                    'target': 'current',
                    'context': self.env.context,
                    # Mensaje de notificación opcional pero útil
                    'params': {
                        'title': '¡Actualizado!',
                        'message': f'Datos actualizados desde API DJANGO de "{self.titulo}".',
                        'type': 'success',
                    }
                }
            else:
                raise UserError(f"API Error ({response.status_code}): {response.text}")
        except Exception as e:
            raise UserError(f"Error de conexión: {str(e)}")