from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from django.db.models import Q
from .models import Libro, Autor
from .serializers import LibroSerializer, AutorSerializer
import requests
import uuid

class AutorViewSet(viewsets.ModelViewSet):
    queryset = Autor.objects.all()
    serializer_class = AutorSerializer

class LibroViewSet(viewsets.ModelViewSet):
    queryset = Libro.objects.select_related('autor').all()
    serializer_class = LibroSerializer

    @action(detail=False, methods=['get'])
    def buscar(self, request):
        """
        Búsqueda Híbrida Inteligente.
        Uso: /api/libros/buscar/?q=Harry Potter
        """
        query = request.query_params.get('q', '').strip()
        if not query:
            return Response(
                {'mensaje': 'Escribe algo en ?q=', 'ejemplo': '/api/libros/buscar/?q=Cien años'}, 
                status=status.HTTP_400_BAD_REQUEST
            )

        print(f"--> Buscando: '{query}'")

        # 1. BÚSQUEDA LOCAL (Primero en casa)
        locales = self.queryset.filter(
            Q(titulo__icontains=query) | 
            Q(isbn__icontains=query) |
            Q(autor__nombre__icontains=query)
        )
        if locales.exists():
            print("--> ¡Encontrado en Base de Datos Local!")
            return Response(self.get_serializer(locales, many=True).data)

        # 2. BÚSQUEDA EN INTERNET (OpenLibrary)
        print("--> No está local. Saliendo a OpenLibrary...")
        try:
            # Buscamos en la API externa
            url = "https://openlibrary.org/search.json"
            resp = requests.get(url, params={'q': query, 'limit': 1}, timeout=8)
            
            if resp.status_code != 200:
                return Response({'error': 'OpenLibrary no responde'}, status=status.HTTP_502_BAD_GATEWAY)

            data = resp.json()
            docs = data.get('docs', [])
            
            if not docs:
                return Response({'mensaje': 'No se encontró ni aquí ni en China.'}, status=status.HTTP_404_NOT_FOUND)

            info = docs[0]
            
            # --- GUARDADO AUTOMÁTICO (Persistencia) ---
            
            # 1. ISBN (Si no trae, generamos uno temporal para no romper la BD)
            isbn_api = info.get('isbn', [''])[0]
            if not isbn_api: 
                isbn_api = f"GEN-{uuid.uuid4().hex[:10].upper()}"
            
            # 2. Datos básicos
            titulo_api = info.get('title', 'Sin Título')[:250]
            autor_nombre = info.get('author_name', ['Desconocido'])[0]

            # 3. Crear Autor
            autor_obj, _ = Autor.objects.get_or_create(nombre=autor_nombre)

            # 4. Crear Libro (evitando duplicados por ISBN)
            nuevo_libro, created = Libro.objects.get_or_create(
                isbn=isbn_api,
                defaults={
                    'titulo': titulo_api,
                    'autor': autor_obj,
                    'imagen_url': f"https://covers.openlibrary.org/b/id/{info.get('cover_i', '')}-M.jpg" if info.get('cover_i') else None,
                    'editorial': info.get('publisher', [''])[0][:140],
                    'paginas': info.get('number_of_pages_median', 0),
                    'estado': 'disponible'
                }
            )
            
            accion = "¡IMPORTADO!" if created else "RECUPERADO"
            print(f"--> {accion}: {nuevo_libro.titulo}")
            
            return Response(self.get_serializer([nuevo_libro], many=True).data)

        except requests.exceptions.RequestException as e:
            return Response({'error': 'Sin conexión a internet', 'detalle': str(e)}, status=status.HTTP_503_SERVICE_UNAVAILABLE)