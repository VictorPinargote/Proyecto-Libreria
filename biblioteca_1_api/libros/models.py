from django.db import models

class Autor(models.Model):
    nombre = models.CharField(max_length=150)
    # Dejamos apellido opcional o integrado en nombre, pero para limpiar usamos solo nombre completo si quieres
    # O mantenemos la estructura simple
    nacionalidad = models.CharField(max_length=100, blank=True, null=True)

    def __str__(self):
        return self.nombre

class Libro(models.Model):
    titulo = models.CharField(max_length=255)
    isbn = models.CharField(max_length=20, unique=True)
    autor = models.ForeignKey(Autor, on_delete=models.CASCADE, related_name='libros')
    
    # Campos enriquecidos (lo que queríamos del otro repo pero bien hecho)
    descripcion = models.TextField(blank=True, null=True)
    imagen_url = models.URLField(max_length=500, blank=True, null=True)
    editorial = models.CharField(max_length=150, blank=True, null=True)
    paginas = models.IntegerField(default=0)
    
    # Estado simple
    estado = models.CharField(
        max_length=20, 
        choices=[('disponible', 'Disponible'), ('agotado', 'Agotado')], 
        default='disponible'
    )

    def __str__(self):
        return self.titulo