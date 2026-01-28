from django.shortcuts import render, redirect
from django.contrib import messages
from django.conf import settings
from rest_framework import viewsets
from .models import Libro, Autor
from .serializers import LibroSerializer
import requests
import xmlrpc.client

# =======================================================
# 1. API REST (Seguridad Token)
# =======================================================
class LibroViewSet(viewsets.ModelViewSet):
    queryset = Libro.objects.all().order_by('-id')
    serializer_class = LibroSerializer

# =======================================================
# 2. CONEXIÓN ODOO
# =======================================================
def empujar_a_odoo(libro_obj):
    """Envía el libro ya guardado en Django hacia Odoo"""
    try:
        url = getattr(settings, 'ODOO_URL', '')
        db = getattr(settings, 'ODOO_DB', '')
        user = getattr(settings, 'ODOO_USER', '')
        password = getattr(settings, 'ODOO_PASS', '')

        common = xmlrpc.client.ServerProxy(f'{url}/xmlrpc/2/common')
        uid = common.authenticate(db, user, password, {})

        if not uid: return False, "Error de credenciales Odoo"

        models = xmlrpc.client.ServerProxy(f'{url}/xmlrpc/2/object')

        # 1. Crear/Buscar Autor
        autor_id = models.execute_kw(db, uid, password, 'biblioteca.autor', 'create', [{'nombre': libro_obj.autor.nombre}])

        # 2. Crear Libro
        vals = {
            'isbn': libro_obj.isbn,
            'titulo': libro_obj.titulo,
            'autor_id': autor_id,
            'paginas': libro_obj.paginas,
            'editorial': libro_obj.editorial,
            'estado': 'disponible'
        }
        
        # Verificar duplicados por ISBN
        existe = models.execute_kw(db, uid, password, 'biblioteca.libro', 'search', [[['isbn', '=', libro_obj.isbn]]])
        if not existe:
            models.execute_kw(db, uid, password, 'biblioteca.libro', 'create', [vals])
            return True, "Creado en Odoo"
        return True, "Ya existía en Odoo"

    except Exception as e:
        return False, f"Fallo Odoo: {str(e)}"

# =======================================================
# 3. VISTAS WEB (EL CEREBRO)
# =======================================================

def catalogo_view(request):
    libros = Libro.objects.all().order_by('-id')
    return render(request, 'libros/catalogo.html', {'libros': libros})

def buscador_view(request):
    datos_json = None  # Este es el JSON intermedio que pediste
    query = request.GET.get('q', '').strip()

    # --- PASO 1: OBTENER DATOS (GET) ---
    if query:
        try:
            # Buscamos campos específicos para asegurar calidad
            url = "https://openlibrary.org/search.json"
            resp = requests.get(url, params={
                'q': query, 
                'limit': 1,
                'fields': 'title,author_name,isbn,publisher,number_of_pages,number_of_pages_median,cover_i,first_publish_year'
            }, timeout=10)
            
            data = resp.json()
            
            if data.get('docs'):
                info = data['docs'][0]
                
                # --- AQUÍ ARMAMOS EL JSON INTERMEDIO ---
                # Validamos cada campo para que no llegue vacío
                
                # Titulo
                titulo = info.get('title', 'Sin Título')
                
                # ISBN (Tomamos el primero o generamos S/N)
                isbn = 'S/N'
                if info.get('isbn'):
                    isbn = info[0] if isinstance(info['isbn'], list) else info['isbn']
                
                # Autor (Unimos lista si hay varios)
                autor = 'Desconocido'
                if info.get('author_name'):
                    autor = info['author_name'][0]
                
                # Páginas (Prioridad: pages -> median -> 0)
                paginas = info.get('number_of_pages', 0)
                if not paginas:
                    paginas = info.get('number_of_pages_median', 0)
                
                # Editorial
                editorial = ''
                if info.get('publisher'):
                    editorial = info['publisher'][0]

                # Portada
                cover = ''
                if info.get('cover_i'):
                    cover = f"https://covers.openlibrary.org/b/id/{info['cover_i']}-L.jpg"

                # ESTE ES EL JSON QUE SE MUESTRA EN PANTALLA
                datos_json = {
                    'titulo': titulo,
                    'isbn': isbn,
                    'autor': autor,
                    'paginas': paginas,
                    'editorial': editorial,
                    'cover': cover,
                    'anio': info.get('first_publish_year', '')
                }
        except Exception as e:
            messages.error(request, f"Error buscando en API: {e}")

    # --- PASO 2: GUARDAR DATOS (POST) ---
    if request.method == 'POST':
        # Recogemos los datos DEL FORMULARIO (que vienen del JSON visualizado)
        accion = request.POST.get('accion')
        
        try:
            # 1. Guardar en Django (Local)
            autor_nombre = request.POST.get('autor', 'Desconocido')
            autor_obj, _ = Autor.objects.get_or_create(nombre=autor_nombre)
            
            libro_obj, created = Libro.objects.update_or_create(
                isbn=request.POST.get('isbn', 'S/N'),
                defaults={
                    'titulo': request.POST.get('titulo'),
                    'autor': autor_obj,
                    'paginas': request.POST.get('paginas') or 0,
                    'editorial': request.POST.get('editorial'),
                    'imagen_url': request.POST.get('cover')
                }
            )

            # 2. Ejecutar Acción
            if accion == 'odoo':
                # Intentar enviar a Odoo
                exito, msg = empujar_a_odoo(libro_obj)
                if exito:
                    messages.success(request, f"✅ Guardado Local y Odoo: {msg}")
                else:
                    messages.warning(request, f"⚠️ Guardado Local, pero falló Odoo: {msg}")
            else:
                messages.success(request, "✅ Guardado correctamente en Local.")
            
            return redirect('catalogo')
            
        except Exception as e:
            messages.error(request, f"Error al procesar: {e}")

    return render(request, 'libros/buscador.html', {'libro': datos_json, 'query': query})