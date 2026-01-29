from django.urls import path, include
from .views import *
from django.contrib.auth import views as auth_views

urlpatterns = [
    path("", index, name="index"),
    
    #Gestion de usuarios
    path('login/', auth_views.LoginView.as_view(), name="login"),
    path('logout/', auth_views.LogoutView.as_view(next_page='login'), name="logout"),
                                                  
    #Cambio de contrasena
    path('password/change', auth_views.PasswordChangeView.as_view(), name="password_change"),
    path('password/change/done', auth_views.PasswordChangeDoneView.as_view(), name="password_change_done"),
    
    #Registro de usuarios
    path('registro/', registro, name="registro"),
    
    #libros
    path('libros/', lista_libros, name="lista_libros"),
    path('libros/nuevo/', crear_libro, name="crear_libro"),
    path('libros/<int:id>/', detalle_libro, name="detalle_libro"),
    path('libros/<int:id>/editar/', editar_libro, name="editar_libro"),
    path('libros/<int:id>/eliminar/', eliminar_libro, name="eliminar_libro"),
    
    #Autores
    path('autores/', lista_autores, name="lista_autores"),
    path('autores/nuevo/', crear_autor, name="crear_autores"),
    path('autores/<int:id>/', detalle_autor, name="detalle_autor"),
    path('autores/<int:id>/editar/', editar_autor, name="editar_autor"),
    path('autores/<int:id>/eliminar/', eliminar_autor, name="eliminar_autor"),
    
    #Prestamos
    path('prestamos/', lista_prestamos, name="lista_prestamos"),
    path('prestamos/nuevo/', crear_prestamo, name="crear_prestamo"),
    path('prestamos/<int:id>', detalle_prestamo, name="detalle_prestamo"),
    path('prestamos/<int:prestamo_id>/devolver/', devolver_libro, name='devolver_libro'),
    
    #Multas
    path('multas/', lista_multas, name="lista_multas"),
    path('multas/nuevo/<int:prestamo_id>', crear_multa, name="crear_multa"),
    path('multas/<int:multa_id>/pagar/', pagar_multa, name='pagar_multa'),
    path('prestamos/<int:prestamo_id>/renovar/', renovar_prestamo, name='renovar_prestamo'),
    
    # Solicitudes de Préstamos (Sistema de solicitudes para usuarios normales)
    path('solicitar-prestamo/', crear_solicitud, name='crear_solicitud'),
    path('mis-solicitudes/', mis_solicitudes, name='mis_solicitudes'),
    path('solicitudes/', lista_solicitudes, name='lista_solicitudes'),
    path('solicitudes/<int:solicitud_id>/aprobar/', aprobar_solicitud, name='aprobar_solicitud'),
    path('solicitudes/<int:solicitud_id>/rechazar/', rechazar_solicitud, name='rechazar_solicitud'),
    
    # Gestión de Usuarios (Solo Admin y Superusuario)
    path('usuarios/', lista_usuarios, name='lista_usuarios'),
    path('usuarios/nuevo/', crear_usuario, name='crear_usuario'),
    path('usuarios/<int:user_id>/editar/', editar_usuario, name='editar_usuario'),
    path('usuarios/<int:user_id>/eliminar/', eliminar_usuario, name='eliminar_usuario'),
    
    # Logs de Actividad (Solo Admin y Superusuario)
    path('logs/', lista_logs, name='lista_logs'),
    
    # Gestión de Stock (Bodeguero)
    path('stock/', gestionar_stock, name='gestionar_stock'),
    
    # API OpenLibrary
    path('api/libros/', api_buscar_libros, name='api_buscar_libros'),
    path('api/autores/', api_buscar_autores, name='api_buscar_autores'),
    
    # --- MODULO API (Refactorizado) ---
    path('api/', include('gestion.api_custom.urls')),
]