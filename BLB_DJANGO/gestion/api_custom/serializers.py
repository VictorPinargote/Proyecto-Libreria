from rest_framework import serializers
from gestion.models import Libro, Autor

class LibroSerializer(serializers.ModelSerializer):
    # Esto ayuda a Odoo a leer el nombre del autor y no solo el ID
    autor_nombre = serializers.ReadOnlyField(source='autor.nombre')

    class Meta:
        model = Libro
        fields = '__all__'