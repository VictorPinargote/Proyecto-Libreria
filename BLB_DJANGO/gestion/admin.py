from django.contrib import admin
from django.contrib.auth.models import Group
from .models import *
# Register your models here.

# Quitar "Grupos" del admin (viene por defecto en Django)
admin.site.unregister(Group)

admin.site.register(Autor)  #para ver los autores en la pagina de adminstracion, es necesario importar el objeto o modulo tambien con 
admin.site.register(Prestamo) #asi podemos ver los prestamos en la pagina de administracion, pero no podemos ver los detalles del prestamo
admin.site.register(Libro)
admin.site.register(Multa)
admin.site.register(Perfil)
admin.site.register(SolicitudPrestamo)
admin.site.register(RegistroActividad)