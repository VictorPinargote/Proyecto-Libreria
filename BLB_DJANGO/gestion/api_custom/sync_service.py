import json, os
from django.conf import settings
from gestion.models import Libro
from django.db.models.signals import post_save, post_delete
from django.dispatch import receiver

JSON_PATH = os.path.join(settings.BASE_DIR, 'gestion', 'api_custom', 'libros_local.json')

def exportar_libros_json():
    try:
        data = []
        for l in Libro.objects.all():
            desc = l.descripcion or ""
            isbn, edit, pags = "S/N", "Desconocido", 0
            
            # Parsear descripción
            for p in desc.split("|"):
                if "ISBN:" in p: isbn = p.replace("ISBN:", "").strip()
                if "Editorial:" in p: edit = p.replace("Editorial:", "").strip()
                if "Páginas:" in p: 
                    try: pags = int(p.replace("Páginas:", "").strip())
                    except: pass
            
            # Prioridad: URL guardada > Generada por ISBN
            cover = l.imagen_url if l.imagen_url else (f"https://covers.openlibrary.org/b/isbn/{isbn.replace('-','')}-L.jpg" if isbn != "S/N" else "")
            
            data.append({
                'titulo': l.titulo,
                'isbn': isbn,
                'autor': f"{l.autor.nombre} {l.autor.apellido}" if l.autor else "Desconocido",
                'editorial': edit,
                'paginas': pags,
                'descripcion': desc,
                'anio': l.anio_publicacion or 0,
                'stock': l.stock,
                'cover': cover,
                'origen': 'Django JSON Cache'
            })
            
        with open(JSON_PATH, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        print(f"[SYNC] OK: {len(data)} libros.")
        
    except Exception as e:
        print(f"[SYNC ERROR] {e}")

@receiver(post_save, sender=Libro)
def actualizar_json_save(sender, instance, **kwargs):
    exportar_libros_json()

@receiver(post_delete, sender=Libro)
def actualizar_json_delete(sender, instance, **kwargs):
    exportar_libros_json()
