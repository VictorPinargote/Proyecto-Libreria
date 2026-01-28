from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import LibroViewSet, buscador_view, catalogo_view

router = DefaultRouter()
router.register(r'libros', LibroViewSet) # Esto genera el /api/libros/

urlpatterns = [
    path('api/', include(router.urls)),           # API con Token
    path('catalogo/', catalogo_view, name='catalogo'), # Tu lista de libros bonita
    path('buscar/', buscador_view, name='buscador'),   # Tu importador con 2 botones
    path('', catalogo_view), # Redirecciona la raíz al catálogo
] 