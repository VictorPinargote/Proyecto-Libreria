from django.shortcuts import render, redirect, get_object_or_404
from django.http import JsonResponse
import requests
import re #se usa para?
from rest_framework import viewsets
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.authtoken.models import Token
from django.contrib.auth.decorators import login_required
from django.views.decorators.csrf import csrf_exempt
from gestion.models import Libro, Autor
from .serializers import LibroSerializer
import json
import os
from django.conf import settings

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
            es_de_openlibrary=True,
            imagen_url=cover_url # Guardamos la URL directa (User Request: Solo URL, no archivo físico)
        )
        
        return redirect('api_gestion_libros')

    return render(request, 'gestion/templates/api_agregar_libro.html')

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def api_proxy_openlibrary(request):
    """
    Endpoint EXCLUSIVO de Datos Locales (JSON).
    Ya no consulta OpenLibrary. Solo devuelve lo que está en libros_local.json.
    """
    q = request.GET.get('q', '').strip()
    if not q: return JsonResponse({'error': 'Vacío'}, status=400)
    
    # Ruta al JSON generado por sync_service.py
    json_path = os.path.join(settings.BASE_DIR, 'gestion', 'api_custom', 'libros_local.json')
    
    libro_encontrado_list = []
    
    if os.path.exists(json_path):
        try:
            with open(json_path, 'r', encoding='utf-8') as f:
                libros_json = json.load(f)
                
            # Buscar en memoria (Case insensitive)
            q_lower = q.lower()
            for l in libros_json:
                # Buscar por título o ISBN
                if q_lower in l.get('titulo', '').lower() or q_lower in l.get('isbn', '').lower():
                    # Asegurar que la URL de la portada sea absoluta
                    if l.get('cover') and not l['cover'].startswith('http'):
                        l['cover'] = request.build_absolute_uri(l['cover'])
                    libro_encontrado_list.append(l)
                    # Si solo queremos el primero, hacemos: break
                    break
        except Exception as e:
            print(f"Error leyendo JSON: {e}")

    if libro_encontrado_list:
        return JsonResponse(libro_encontrado_list, safe=False)
    
    # Si no está en el JSON, devolvemos lista vacía (Odoo entenderá "No encontrado")
    return JsonResponse([], safe=False)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def api_openlibrary_proxy_external(request):
    """
    Endpoint EXCLUSIVO para el Frontend de Django.
    Este SÍ tiene permiso de consultar OpenLibrary para ayudar a crear nuevos libros.
    """
    q = request.GET.get('q', '').strip()
    if not q: return JsonResponse({'error': 'Vacío'}, status=400)
    
    try:
        # Lógica original de OpenLibrary que se eliminó, restaurada solo para este endpoint
        es_isbn = q.replace("-", "").isdigit() and len(q.replace("-", "")) in [10, 13]
        docs = []

        if es_isbn:
            url_isbn = f"https://openlibrary.org/isbn/{q.replace('-', '')}.json"
            resp_isbn = requests.get(url_isbn, timeout=5)
            if resp_isbn.status_code == 200:
                book_data = resp_isbn.json()
                
                autor_nombre = "Desconocido"
                if 'authors' in book_data:
                    key_autor = book_data['authors'][0]['key']
                    try:
                        resp_autor = requests.get(f"https://openlibrary.org{key_autor}.json", timeout=3)
                        if resp_autor.status_code == 200:
                            autor_nombre = resp_autor.json().get('name', 'Desconocido')
                    except: pass
                
                publish_date = book_data.get('publish_date', '')
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

        if not docs:
            url = "https://openlibrary.org/search.json"
            params = {'q': q, 'limit': 1}
            resp = requests.get(url, params=params, timeout=5)
            if resp.status_code == 200:
                docs = resp.json().get('docs', [])

        if docs:
            book = None
            for doc in docs[:5]:
                if doc.get('isbn') and len(doc.get('isbn')) > 0:
                    book = doc
                    break
            if not book: book = docs[0]

            cover_url = ''
            if book.get('cover_i'):
                cover_url = f"https://covers.openlibrary.org/b/id/{book.get('cover_i')}-L.jpg"
            elif es_isbn and book.get('covers'): 
                  cover_url = f"https://covers.openlibrary.org/b/id/{book.get('covers')[0]}-L.jpg"

            isbn_list = book.get('isbn', [])
            isbn_final = "S/N"
            if isinstance(isbn_list, list):
                for code in isbn_list:
                     if len(code) == 13 and code.startswith('978'):
                         isbn_final = code
                         break
                if isbn_final == "S/N" and len(isbn_list) > 0:
                     isbn_final = isbn_list[0]
            else:
                 isbn_final = isbn_list or "S/N"
                 
            publish_date = book.get('publish_date', '')
            if isinstance(publish_date, list): publish_date = publish_date[0]
            anio_str = ''.join(filter(str.isdigit, str(publish_date)))[:4]
            
            editorial_val = "Desconocido"
            pubs = book.get('publisher', [])
            if isinstance(pubs, list) and len(pubs) > 0:
                editorial_val = pubs[0]
            elif isinstance(pubs, str):
                editorial_val = pubs

            data = {
                'titulo': book.get('title'),
                'isbn': isbn_final,
                'autor': book.get('author_name', ['Desconocido'])[0] if isinstance(book.get('author_name'), list) else book.get('author_name'),
                'editorial': editorial_val,
                'paginas': book.get('number_of_pages_median', 0) or book.get('number_of_pages', 0),
                'anio': anio_str or 0,
                'cover': cover_url,
                'origen': 'OpenLibrary API (Internet)'
            }
            return JsonResponse([data], safe=False) # Frontend espera lista

    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)
    
    return JsonResponse([], safe=False)


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def api_exportar_libro(request, libro_id):
    """Marca un libro como disponible para Odoo (en_odoo=True)"""
    try:
        libro = get_object_or_404(Libro, pk=libro_id)
        libro.en_odoo = True
        libro.save()
        return JsonResponse({'status': 'ok', 'message': f'Libro {libro.id} exportado correctamente.'})
    except Exception as e:
        return JsonResponse({'status': 'error', 'message': str(e)}, status=500)

