from django.shortcuts import render, redirect, get_object_or_404
from django.http import JsonResponse
import requests
from rest_framework import viewsets
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.authtoken.models import Token
from django.contrib.auth.decorators import login_required
from django.views.decorators.csrf import csrf_exempt
from gestion.models import Libro, Autor
from .serializers import LibroSerializer

# =====================================================
# 1. VIEWSETS (Endpoints de Datos para Odoo)
# =====================================================

from rest_framework import viewsets, filters

class LibroAPIViewSet(viewsets.ModelViewSet):
    """
    API endpoint que Odoo consume.
    Solo permite: GET, POST, PUT y DELETE.
    """
    queryset = Libro.objects.all().order_by('-id')
    serializer_class = LibroSerializer
    http_method_names = ['get', 'post', 'put', 'delete']
    filter_backends = [filters.SearchFilter]
    search_fields = ['titulo', 'isbn']


# =====================================================
# 2. INTERFAZ DE ADMINISTRACIÓN API
# =====================================================

@login_required
def api_dashboard(request):
    token, _ = Token.objects.get_or_create(user=request.user)
    return render(request, 'gestion/templates/api_dashboard.html', {'token': token.key})

@login_required
def api_gestion_libros(request):
    """Lista los libros disponibles para la API"""
    libros = Libro.objects.all().order_by('-id')
    return render(request, 'gestion/templates/api_gestion_libros.html', {'libros': libros})

@login_required
def api_agregar_libro(request):
    """Vista para agregar libro manualmente o desde OpenLibrary"""
    if request.method == 'POST':
        titulo = request.POST.get('titulo')
        isbn = request.POST.get('isbn')
        autor_nombre = request.POST.get('autor') # Recibimos nombre, buscamos/creamos objeto
        editorial = request.POST.get('editorial')
        paginas = request.POST.get('paginas')
        stock = request.POST.get('stock', 1)
        anio_publicacion = request.POST.get('anio_publicacion')
        cover_url = request.POST.get('cover_url')

        # Buscar o crear Autor
        autor_obj = None
        if autor_nombre:
            nombre_parts = autor_nombre.split(maxsplit=1)
            nombre = nombre_parts[0]
            apellido = nombre_parts[1] if len(nombre_parts) > 1 else ''
            autor_obj, _ = Autor.objects.get_or_create(
                nombre__iexact=nombre, 
                apellido__iexact=apellido,
                defaults={'nombre': nombre, 'apellido': apellido}
            )

        # Crear Libro
        # Tratar de convertir páginas y año a int, si falla usar None o 0
        try: paginas_int = int(paginas) if paginas else None
        except: paginas_int = None
        
        try: anio_int = int(anio_publicacion) if anio_publicacion else None
        except: anio_int = None

        libro = Libro.objects.create(
            titulo=titulo,
            autor=autor_obj,
            stock=int(stock),
            disponible=True,
            descripcion=f"ISBN: {isbn} | Editorial: {editorial} | Páginas: {paginas}",
            anio_publicacion=anio_int,
            es_de_openlibrary=True 
        )
        
        return redirect('api_gestion_libros')

    return render(request, 'gestion/templates/api_agregar_libro.html')

@login_required
def api_proxy_openlibrary(request):
    """Proxy para buscar en OpenLibrary desde el frontend (evita CORS y lógica en JS puro)"""
    q = request.GET.get('q', '').strip()
    if not q: return JsonResponse({'error': 'Vacío'}, status=400)
    
    try:
        # 1. Intentar buscar como ISBN directo
        # Los ISBN suelen ser numéricos de 10 o 13 dígitos
        es_isbn = q.replace("-", "").isdigit() and len(q.replace("-", "")) in [10, 13]
        
        docs = []
        
        if es_isbn:
            # Búsqueda específica por ISBN (suele dar mejor dato)
            url_isbn = f"https://openlibrary.org/isbn/{q.replace('-', '')}.json"
            resp_isbn = requests.get(url_isbn, timeout=5)
            if resp_isbn.status_code == 200:
                book_data = resp_isbn.json()
                # Adaptamos al formato de search.json para simplificar
                # Necesitamos transformar los datos crudos del ISBN endpoint
                
                # Resolviendo autor (viene como key /authors/Ol123...)
                autor_nombre = "Desconocido"
                if 'authors' in book_data:
                    key_autor = book_data['authors'][0]['key']
                    try:
                        resp_autor = requests.get(f"https://openlibrary.org{key_autor}.json", timeout=3)
                        if resp_autor.status_code == 200:
                            autor_nombre = resp_autor.json().get('name', 'Desconocido')
                    except: pass
                
                publish_date = book_data.get('publish_date', '')
                # Intentar extraer solo el año de strings como "May 2005" o "2005"
                anio = ''.join(filter(str.isdigit, str(publish_date)))[:4]
                
                docs = [{
                    'title': book_data.get('title'),
                    'isbn': [q],
                    'author_name': [autor_nombre],
                    'publisher': book_data.get('publishers', [''])[0],
                    'number_of_pages_median': book_data.get('number_of_pages', 0),
                    'first_publish_year': anio,
                    'cover_i': book_data.get('covers', [None])[0]
                }]

        # 2. Si no es ISBN o falló, usar search general
        if not docs:
            url = "https://openlibrary.org/search.json"
            params = {'q': q, 'limit': 1}
            resp = requests.get(url, params=params, timeout=5)
            if resp.status_code == 200:
                docs = resp.json().get('docs', [])

        if docs:
            book = docs[0]
            cover_url = ''
            if book.get('cover_i'):
                cover_url = f"https://covers.openlibrary.org/b/id/{book.get('cover_i')}-L.jpg"
            elif es_isbn and book.get('covers'): # Soporte para el formato directo de ISBN que guarda lista de IDs
                 cover_url = f"https://covers.openlibrary.org/b/id/{book.get('covers')[0]}-L.jpg"

            data = {
                'titulo': book.get('title'),
                'isbn': book.get('isbn', [''])[0] if isinstance(book.get('isbn'), list) else book.get('isbn'),
                'autor': book.get('author_name', ['Desconocido'])[0] if isinstance(book.get('author_name'), list) else book.get('author_name'),
                'editorial': book.get('publisher', [''])[0] if isinstance(book.get('publisher'), list) else book.get('publisher'),
                'paginas': book.get('number_of_pages_median', 0) or book.get('number_of_pages', 0),
                'anio': book.get('first_publish_year') or book.get('publish_year', [0])[0] if isinstance(book.get('publish_year'), list) else book.get('publish_year'),
                'cover': cover_url
            }
            return JsonResponse(data)
            
        return JsonResponse({'error': 'No encontrado'}, status=404)
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)

