import json
import os
import re
from django.conf import settings
from gestion.models import Libro
from django.db.models.signals import post_save, post_delete
from django.dispatch import receiver

JSON_PATH = os.path.join(settings.BASE_DIR, 'gestion', 'api_custom', 'libros_local.json')

def exportar_libros_json():
    """
    Exporta todos los libros de la base de datos a un archivo JSON.
    Parsea la descripción para obtener metadatos extra si no existen en el modelo.
    """
    try:
        libros = Libro.objects.all()
        lista_data = []

        for libro in libros:
            # Valores por defecto
            isbn_val = "S/N"
            editorial_val = "Desconocido"
            paginas_val = 0
            
            # Intentar parsear descripción
            desc = libro.descripcion or ""
            try:
                parts = desc.split("|")
                for p in parts:
                    p = p.strip()
                    if "ISBN:" in p: isbn_val = p.replace("ISBN:", "").strip()
                    if "Editorial:" in p: editorial_val = p.replace("Editorial:", "").strip()
                    if "Páginas:" in p: 
                        try: paginas_val = int(p.replace("Páginas:", "").strip())
                        except: pass
            except: pass
            
            # Si el modelo tuviera campo ISBN, usarlo (pero parece que no tiene)
            if hasattr(libro, 'isbn') and libro.isbn:
                isbn_val = libro.isbn

            # LÓGICA DE PORTADA (Prioridad: OpenLibrary URL > Local URL Field > Local Image File)
            cover_url = ""
            
            # 1. Si tiene ISBN válido, generamos URL de OpenLibrary
            if isbn_val and isbn_val != "S/N":
                clean_isbn = isbn_val.replace("-", "").strip()
                cover_url = f"https://covers.openlibrary.org/b/isbn/{clean_isbn}-L.jpg"
            
            # 2. Si hay URL guardada explícitamente (nuevo sistema)
            elif hasattr(libro, 'imagen_url') and libro.imagen_url:
                cover_url = libro.imagen_url
            
            # (Eliminado: Ya no usamos imágenes físicas locales)
            
            # Construir objeto
            data = {
                'titulo': libro.titulo,
                'isbn': isbn_val,
                'autor': f"{libro.autor.nombre} {libro.autor.apellido}" if libro.autor else "Desconocido",
                'editorial': editorial_val,
                'paginas': paginas_val,
                'descripcion': desc,
                'anio': libro.anio_publicacion or 0,
                'stock': libro.stock,
                'cover': cover_url,
                'origen': 'Django JSON Cache'
            }
            lista_data.append(data)

        # Escribir archivo
        with open(JSON_PATH, 'w', encoding='utf-8') as f:
            json.dump(lista_data, f, ensure_ascii=False, indent=2)
            
        print(f"[SYNC] Exportados {len(lista_data)} libros a {JSON_PATH}")
        
    except Exception as e:
        print(f"[SYNC ERROR] {e}")

@receiver(post_save, sender=Libro)
def actualizar_json_save(sender, instance, **kwargs):
    exportar_libros_json()

@receiver(post_delete, sender=Libro)
def actualizar_json_delete(sender, instance, **kwargs):
    exportar_libros_json()
