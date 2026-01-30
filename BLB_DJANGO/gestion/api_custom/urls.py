from django.urls import path
from .views import (
    api_dashboard, api_gestion_libros, api_agregar_libro,
    api_editar_libro, api_eliminar_libro,
    api_exportar_libro, api_proxy_openlibrary, api_openlibrary_proxy_external
)

urlpatterns = [
    path('', api_dashboard, name='api_dashboard'),
    path('gestion/', api_gestion_libros, name='api_gestion_libros'),
    path('gestion/agregar/', api_agregar_libro, name='api_agregar_libro'),
    path('gestion/editar/<int:libro_id>/', api_editar_libro, name='api_editar_libro'),
    path('gestion/eliminar/<int:libro_id>/', api_eliminar_libro, name='api_eliminar_libro'),
    path('gestion/exportar/<int:libro_id>/', api_exportar_libro, name='api_exportar_libro'),
    path('proxy/openlibrary/', api_proxy_openlibrary, name='api_proxy_openlibrary'),
    path('proxy/openlibrary-external/', api_openlibrary_proxy_external, name='api_openlibrary_proxy_external'),
]
