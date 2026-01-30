from rest_framework import serializers
from gestion.models import Libro, Autor

class LibroSerializer(serializers.ModelSerializer):
    # Esto ayuda a Odoo a leer el nombre del autor y no solo el ID
    autor_nombre = serializers.ReadOnlyField(source='autor.nombre')

    class Meta:
        model = Libro
        # Excluimos 'id' e 'imagen' (física) y campos inexistentes para evitar 500 error.
        fields = [
            'titulo', 'autor_nombre', 'autor', 
            'descripcion', 'anio_publicacion',
            'stock', 'disponible', 'es_de_openlibrary', 
            'en_odoo', 'imagen_url'
        ]