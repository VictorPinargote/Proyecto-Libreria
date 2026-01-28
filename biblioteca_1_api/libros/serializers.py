from rest_framework import serializers
from .models import Libro, Autor

class AutorSerializer(serializers.ModelSerializer):
    class Meta:
        model = Autor
        fields = '__all__'

class LibroSerializer(serializers.ModelSerializer):
    # Enviamos el nombre del autor "plano" para que Odoo lo lea fácil
    autor_nombre = serializers.SerializerMethodField()

    class Meta:
        model = Libro
        fields = '__all__'

    def get_autor_nombre(self, obj):
        return str(obj.autor.nombre)