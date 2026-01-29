from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import (
    LibroAPIViewSet, api_dashboard, 
    api_gestion_libros, api_agregar_libro, api_proxy_openlibrary
)

# Router para los ViewSets (DRF)
router = DefaultRouter()
router.register(r'libros', LibroAPIViewSet)

urlpatterns = [
    # 1. El Dashboard es la "Home" de /api/
    path('', api_dashboard, name='api_dashboard'),
    
    # 2. Interfaz de Gestión (Estilo Biblioteca)
    path('gestion/', api_gestion_libros, name='api_gestion_libros'),
    path('gestion/agregar/', api_agregar_libro, name='api_agregar_libro'),
    path('proxy/openlibrary/', api_proxy_openlibrary, name='api_proxy_openlibrary'),
    
    # 3. Las rutas del router se incluyen también bajo /api/
    # Ejemplo: /api/libros/
    path('', include(router.urls)),
]
