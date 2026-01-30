from django.shortcuts import render, redirect, get_object_or_404
from django.http import JsonResponse
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.authtoken.models import Token
from django.contrib.auth.decorators import login_required
from gestion.models import Libro, Autor
import requests, json, os
from django.conf import settings

# --- API VISUAL (Restaurada) ---

@login_required
def api_dashboard(request):
    token, _ = Token.objects.get_or_create(user=request.user)
    return render(request, 'gestion/templates/api_dashboard.html', {'token': token.key})

@login_required
def api_gestion_libros(request):
    return render(request, 'gestion/templates/api_gestion_libros.html', {'libros': Libro.objects.all().order_by('-id')})

@login_required
def api_agregar_libro(request):
    if request.method == 'POST':
        data = request.POST
        # Buscar/Crear Autor
        autor_obj = None
        if data.get('autor'):
            parts = data.get('autor').split(maxsplit=1)
            autor_obj, _ = Autor.objects.get_or_create(
                nombre__iexact=parts[0], 
                defaults={'nombre': parts[0], 'apellido': parts[1] if len(parts) > 1 else ''}
            )

        # Crear Libro
        Libro.objects.create(
            titulo=data.get('titulo'),
            autor=autor_obj,
            stock=int(data.get('stock', 1)),
            disponible=True,
            descripcion=f"ISBN: {data.get('isbn')} | Editorial: {data.get('editorial')} | Páginas: {data.get('paginas')}",
            anio_publicacion=int(data.get('anio_publicacion')) if data.get('anio_publicacion') else None,
            es_de_openlibrary=True,
            imagen_url=data.get('cover_url')
        )
        return redirect('api_gestion_libros')
    return render(request, 'gestion/templates/api_agregar_libro.html')

@api_view(['POST'])
@permission_classes([IsAuthenticated])
def api_exportar_libro(request, libro_id):
    try:
        l = get_object_or_404(Libro, pk=libro_id)
        l.en_odoo = True
        l.save()
        return JsonResponse({'status': 'ok'})
    except Exception as e:
        return JsonResponse({'status': 'error', 'message': str(e)}, status=500)

@login_required
def api_editar_libro(request, libro_id):
    libro = get_object_or_404(Libro, id=libro_id)
    if request.method == 'POST':
        libro.titulo = request.POST.get('titulo')
        if request.POST.get('autor'):
            parts = request.POST.get('autor').split(maxsplit=1)
            autor_obj, _ = Autor.objects.get_or_create(
                nombre__iexact=parts[0], 
                defaults={'nombre': parts[0], 'apellido': parts[1] if len(parts) > 1 else ''}
            )
            libro.autor = autor_obj
        
        libro.stock = int(request.POST.get('stock', libro.stock))
        libro.anio_publicacion = int(request.POST.get('anio_publicacion')) if request.POST.get('anio_publicacion') else None
        libro.imagen_url = request.POST.get('cover_url', libro.imagen_url)
        
        # Reconstruir descripción
        isbn = request.POST.get('isbn', 'S/N')
        edit = request.POST.get('editorial', 'Desconocido')
        pags = request.POST.get('paginas', '0')
        libro.descripcion = f"ISBN: {isbn} | Editorial: {edit} | Páginas: {pags}"
        
        libro.save() # Esto dispara la señal para actualizar el JSON
        return redirect('api_gestion_libros')
    
    # Parsear descripción para el template
    desc = libro.descripcion or ""
    metadata = {'isbn': '', 'editorial': '', 'paginas': ''}
    for p in desc.split("|"):
        if "ISBN:" in p: metadata['isbn'] = p.replace("ISBN:", "").strip()
        if "Editorial:" in p: metadata['editorial'] = p.replace("Editorial:", "").strip()
        if "Páginas:" in p: metadata['paginas'] = p.replace("Páginas:", "").strip()
        
    return render(request, 'gestion/templates/api_editar_libro.html', {'libro': libro, 'meta': metadata})

@login_required
def api_eliminar_libro(request, libro_id):
    libro = get_object_or_404(Libro, id=libro_id)
    if request.method == 'POST':
        libro.delete() # Esto dispara la señal para actualizar el JSON
        return redirect('api_gestion_libros')
    return redirect('api_gestion_libros')

# --- PROXIES (Esenciales) ---

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def api_proxy_openlibrary(request):
    """
    1. PROXY PRIVADO (Para Odoo):
    Lee TU archivo libros_local.json. Odoo consume esto.
    """
    q = request.GET.get('q', '').strip().lower()
    if not q: return JsonResponse({'error': 'Vacío'}, status=400)
    
    json_path = os.path.join(settings.BASE_DIR, 'gestion', 'api_custom', 'libros_local.json')
    if os.path.exists(json_path):
        try:
            with open(json_path, 'r', encoding='utf-8') as f:
                for l in json.load(f):
                    if q in l.get('titulo', '').lower() or q in l.get('isbn', '').lower():
                        return JsonResponse([l], safe=False)
        except: pass
    return JsonResponse([], safe=False)

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def api_openlibrary_proxy_external(request):
    """
    2. PROXY EXTERNO (Para tu Frontend Django):
    Consulta a OpenLibrary.org para autocompletar formularios.
    """
    q = request.GET.get('q', '').strip()
    if not q: return JsonResponse({'error': 'Vacío'}, status=400)
    
    try:
        docs = []
        # Búsqueda por ISBN
        if q.replace("-", "").isdigit():
            r = requests.get(f"https://openlibrary.org/isbn/{q.replace('-', '')}.json", timeout=5)
            if r.status_code == 200:
                bd = r.json()
                docs = [{'title': bd.get('title'), 'isbn': [q], 'cover_i': bd.get('covers', [None])[0],
                         'author_name': ['Desconocido'], 'publisher': bd.get('publishers', [''])[0],
                         'number_of_pages': bd.get('number_of_pages', 0), 
                         'first_publish_year': str(bd.get('publish_date', ''))[-4:]}]

        # Búsqueda General si falla ISBN
        if not docs:
            r = requests.get("https://openlibrary.org/search.json", params={'q': q, 'limit': 1}, timeout=5)
            if r.status_code == 200: docs = r.json().get('docs', [])

        if docs:
            b = docs[0]
            # Extraer ISBN válido
            isbn = next((c for c in b.get('isbn', []) if len(c)==13 and c.startswith('978')), b.get('isbn', ['S/N'])[0] if b.get('isbn') else "S/N")
            
            # Construir URL Portada
            cover = f"https://covers.openlibrary.org/b/id/{b.get('cover_i')}-L.jpg" if b.get('cover_i') else ""
            if not cover and b.get('isbn'): 
                cover = f"https://covers.openlibrary.org/b/isbn/{b.get('isbn')[0]}-L.jpg"

            return JsonResponse([{
                'titulo': b.get('title'),
                'isbn': isbn,
                'autor': b.get('author_name', ['Desconocido'])[0],
                'editorial': b.get('publisher', ['Desconocido'])[0] if isinstance(b.get('publisher'), list) else b.get('publisher', 'Desconocido'),
                'paginas': b.get('number_of_pages', 0),
                'anio': ''.join(filter(str.isdigit, str(b.get('first_publish_year', ''))))[:4] or 0,
                'cover': cover,
                'origen': 'OpenLibrary API'
            }], safe=False)

    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)
    return JsonResponse([], safe=False)

    return JsonResponse([], safe=False)
