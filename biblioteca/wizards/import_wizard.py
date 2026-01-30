from odoo import models, fields, exceptions
import requests
import base64
import logging

_logger = logging.getLogger(__name__)

class LibroImportWizard(models.TransientModel):
    _name = 'biblioteca.import.wizard'
    _description = 'Importar Libro desde API'

    query = fields.Char('Buscar (ISBN o Título)', required=True)
    api_token = fields.Char('Token API', required=True, default='4af65a4e59810b00c011b906de3ee7703d28f432')
    api_url = fields.Char('URL API', required=True, default='http://127.0.0.1:8000/api/proxy/openlibrary/')
    
    # Campos de previsualización
    preview_isbn = fields.Char('ISBN', readonly=True)
    preview_titulo = fields.Char('Título', readonly=True)
    preview_autor = fields.Char('Autor', readonly=True)
    preview_cover_url = fields.Char('URL Portada', readonly=True)
    preview_editorial = fields.Char('Editorial', readonly=True)
    preview_descripcion = fields.Text('Descripción', readonly=True)
    preview_paginas = fields.Integer('Páginas', readonly=True)
    
    state = fields.Selection([('draft', 'Borrador'), ('found', 'Encontrado')], default='draft')

    def action_buscar(self):
        """Busca el libro en la API de Django"""
        if not self.query:
             raise exceptions.UserError("Por favor escribe un ISBN o Título.")

        headers = {'Authorization': f'Token {self.api_token}'}
        try:
            res = requests.get(self.api_url, params={'q': self.query}, headers=headers, timeout=10)
            
            if res.status_code == 200:
                data_list = res.json()
                if not data_list:
                     raise exceptions.UserError("No se encontraron libros.")
                
                # Tomamos el primero
                data = data_list[0]
                
                # Guardamos los datos en el wizard para previsualizar
                self.write({
                    'preview_isbn': data.get('isbn'),
                    'preview_titulo': data.get('titulo'),
                    'preview_autor': data.get('autor'),
                    'preview_cover_url': data.get('cover'),
                    'preview_editorial': data.get('editorial'),
                    'preview_descripcion': data.get('descripcion'),
                    'preview_paginas': data.get('paginas'),
                    'state': 'found'
                })
                
                return {
                    'type': 'ir.actions.act_window',
                    'res_model': 'biblioteca.import.wizard',
                    'res_id': self.id,
                    'view_mode': 'form',
                    'target': 'new',
                }
            else:
                 raise exceptions.UserError(f"Error API: {res.text}")
                 
        except requests.exceptions.ConnectionError:
            raise exceptions.UserError("No hay conexión con Django. Revisa que el servidor (puerto 8000) esté prendido.")
        except Exception as e:
            raise exceptions.UserError(f"Error al buscar: {str(e)}")

    def action_confirmar(self):
        """Crea el libro en Odoo"""
        
        # 1. EVITAR DUPLICADOS (Si el ISBN ya existe, paramos el carro)
        if self.preview_isbn:
            existe = self.env['biblioteca.libro'].search([('isbn', '=', self.preview_isbn)], limit=1)
            if existe:
                raise exceptions.UserError(f"¡El libro '{existe.titulo}' ya existe con ese ISBN!")

        # 2. DESCARGAR PORTADA (¡OJO AQUÍ ESTABA EL ERROR!)
        img_b64 = False
        if self.preview_cover_url:
            try:
                r = requests.get(self.preview_cover_url, timeout=10)
                if r.status_code == 200:
                    # ODOO TRUCO: Convertir bytes a string base64 utf-8
                    img_b64 = base64.b64encode(r.content).decode('utf-8')
            except Exception as e:
                _logger.warning(f"No se pudo descargar la imagen: {e}")

        # 3. GESTIONAR AUTOR
        autor_nombre = self.preview_autor or 'Desconocido'
        autor = self.env['biblioteca.autor'].search([('nombre', '=', autor_nombre)], limit=1)
        if not autor:
            autor = self.env['biblioteca.autor'].create({'nombre': autor_nombre})

        # 4. CREAR EL LIBRO (Blindado con Try/Except)
        try:
            self.env['biblioteca.libro'].create({
                'isbn': self.preview_isbn or 'S/N',
                'titulo': self.preview_titulo or 'Sin Título',
                'autor_id': autor.id,
                'editorial': self.preview_editorial,
                'descripcion': self.preview_descripcion,
                'paginas': self.preview_paginas,
                'portada': img_b64, # Aquí pasamos la imagen corregida
                'estado': 'disponible'
            })
        except Exception as e:
            # Si falla aquí, te dirá exactamente por qué
            raise exceptions.UserError(f"Error al guardar en Odoo: {str(e)}")
        
        # 5. CERRAR VENTANA
        return {'type': 'ir.actions.act_window_close'}