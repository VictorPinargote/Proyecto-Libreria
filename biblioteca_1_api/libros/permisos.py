from rest_framework import permissions

class EsBibliotecarioOSoloLectura(permissions.BasePermission):
    def has_permission(self, request, view):
        #lectura para todos
        if request.method in permissions.SAFE_METHODS:
            return True
        #es bibliotecario para acciones de escritura
        return request.user and request.user.is_staff
    
class EsPropietarioPrestamo(permissions.BasePermission):
    def has_object_permission(self, request, view, obj):
        if request.user.is_staff:
            return True
        
        return obj.usuario == request.user
    
 