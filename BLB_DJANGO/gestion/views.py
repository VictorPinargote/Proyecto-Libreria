from django.shortcuts import render, redirect, get_object_or_404
from django.db import models
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import User
from django.utils import timezone
from django.conf import settings
from django.http import HttpResponseForbidden, JsonResponse
from django.contrib.auth import login
from functools import wraps
from .openlibrary import buscar_libros, buscar_autores
from .models import Autor, Libro, Prestamo, Multa, Perfil, SolicitudPrestamo, RegistroActividad
from .forms import RegistroUsuarioForm
from datetime import timedelta
import requests

# --- PERMISOS Y UTILIDADES ---

def obtener_rol(user):
    return user.perfil.rol if user.is_authenticated and hasattr(user, 'perfil') else 'usuario'

def requiere_rol(*roles):
    def decorator(view_func):
        @wraps(view_func)
        def _wrapped_view(request, *args, **kwargs):
            if not request.user.is_authenticated: return redirect('login')
            rol = obtener_rol(request.user)
            if rol != 'superusuario' and rol not in roles:
                return HttpResponseForbidden("No tienes permiso.")
            return view_func(request, *args, **kwargs)
        return _wrapped_view
    return decorator

def registrar_log(usuario, tipo, desc, request=None, modelo=None, obj_id=None):
    ip, url = None, None
    if request:
        x_forwarded = request.META.get('HTTP_X_FORWARDED_FOR')
        ip = x_forwarded.split(',')[0] if x_forwarded else request.META.get('REMOTE_ADDR')
        url = request.path
    
    RegistroActividad.objects.create(
        usuario=usuario if usuario and usuario.is_authenticated else None,
        tipo_accion=tipo, descripcion=desc, direccion_ip=ip,
        url=url, modelo_afectado=modelo, objeto_id=obj_id
    )

def index(request):
    ctx = {
        'total_libros': Libro.objects.count(),
        'total_autores': Autor.objects.count(),
        'total_prestamos': Prestamo.objects.filter(fecha_devolucion__isnull=True).count(),
        'total_multas': Multa.objects.filter(pagada=False).aggregate(t=models.Sum('monto'))['t'] or 0,
        'total_stock': Libro.objects.aggregate(t=models.Sum('stock'))['t'] or 0,
        'mis_solicitudes': SolicitudPrestamo.objects.filter(usuario=request.user).count() if request.user.is_authenticated else 0,
        'libros_destacados': Libro.objects.all().order_by('-id')[:8]
    }
    return render(request, 'gestion/templates/home.html', ctx)

def lista_libros(request):
    return render(request, 'gestion/templates/libros.html', {'libros': Libro.objects.all()})

def detalle_libro(request, id):
    libro = get_object_or_404(Libro, id=id)
    puede_editar = request.user.is_authenticated and obtener_rol(request.user) in ['bodeguero', 'superusuario']
    return render(request, 'gestion/templates/detalle_libro.html', {'libro': libro, 'puede_editar': puede_editar})

@requiere_rol('bodeguero')
def editar_libro(request, id):
    libro = get_object_or_404(Libro, id=id)
    if request.method == 'POST':
        libro.titulo = request.POST.get('titulo', libro.titulo)
        if request.POST.get('autor'): libro.autor = get_object_or_404(Autor, id=request.POST.get('autor'))
        libro.descripcion = request.POST.get('descripcion', libro.descripcion)
        libro.stock = int(request.POST.get('stock', libro.stock))
        libro.disponible = request.POST.get('disponible') == 'on'
        if request.POST.get('anio_publicacion'): libro.anio_publicacion = int(request.POST.get('anio_publicacion'))
        if request.FILES.get('imagen'): libro.imagen = request.FILES.get('imagen')
        
        libro.save()
        registrar_log(request.user, 'editar', f'Editó libro: {libro.titulo}', request, 'Libro', libro.pk)
        return redirect('detalle_libro', id=libro.pk)
    
    return render(request, 'gestion/templates/editar_libro.html', {'libro': libro, 'autores': Autor.objects.all()})

@requiere_rol('bodeguero')
def eliminar_libro(request, id):
    libro = get_object_or_404(Libro, id=id)
    if request.method == 'POST':
        try:
            libro.delete()
            registrar_log(request.user, 'eliminar', f'Eliminó libro: {libro.titulo}', request, 'Libro', id)
            return redirect('lista_libros')
        except:
            return render(request, 'gestion/templates/detalle_libro.html', {'libro': libro, 'error': 'No se puede eliminar, tiene préstamos.'})
    return redirect('detalle_libro', id=libro.pk)

@requiere_rol('bodeguero')
def crear_libro(request):
    if request.method == "POST":
        titulo = request.POST.get('titulo')
        autor_id = request.POST.get('autor')
        autor_nombre = request.POST.get('autor_nombre', '')
        
        autor = None
        if autor_id:
            autor = get_object_or_404(Autor, id=autor_id)
        elif autor_nombre:
            partes = autor_nombre.split(',')[0].strip().split()
            nombre = ' '.join(partes[:-1]) if len(partes) >= 2 else autor_nombre
            apellido = partes[-1] if len(partes) >= 2 else ''
            autor, _ = Autor.objects.get_or_create(nombre__iexact=nombre, apellido__iexact=apellido, defaults={'nombre': nombre, 'apellido': apellido})
        
        if titulo and autor:
            libro = Libro.objects.create(
                titulo=titulo, autor=autor, 
                stock=int(request.POST.get('stock', 1)),
                disponible=request.POST.get('disponible') == 'on',
                descripcion=request.POST.get('descripcion', ''),
                anio_publicacion=int(request.POST.get('anio_publicacion')) if request.POST.get('anio_publicacion') else None,
                es_de_openlibrary=request.POST.get('es_de_openlibrary') == 'true'
            )
            
            if request.FILES.get('imagen'):
                libro.imagen = request.FILES.get('imagen')
                libro.save()
            elif request.POST.get('imagen_url'):
                try:
                    from django.core.files.base import ContentFile
                    resp = requests.get(request.POST.get('imagen_url'), timeout=10)
                    if resp.status_code == 200:
                        libro.imagen.save(f"libro_{libro.pk}.jpg", ContentFile(resp.content), save=True)
                except: pass
            
            registrar_log(request.user, 'crear', f'Creó libro: {titulo}', request, 'Libro', libro.pk)
            return redirect('lista_libros')
            
    return render(request, 'gestion/templates/crear_libros.html', {'autores': Autor.objects.all()})

def lista_prestamos(request):
    qs = Prestamo.objects.filter(usuario=request.user) if obtener_rol(request.user) == 'usuario' else Prestamo.objects.all()
    return render(request, 'gestion/templates/prestamos.html', {'prestamos': qs})

def lista_autores(request):
    return render(request, 'gestion/templates/autores.html', {'autores': Autor.objects.all()})
        
@requiere_rol('bodeguero')
def crear_autor(request, id=None):
    if id == None:
        autor = None
        modo = 'crear'
    else:
        autor = get_object_or_404(Autor, id=id)
        modo = 'editar'
        
    if request.method == 'POST': #si ya envia datos y captura en variabes para poder crear el autor
        nombre = request.POST.get('nombre')
        apellido = request.POST.get('apellido')
        bibliografia = request.POST.get('bibliografia')
        if autor == None:
            Autor.objects.create(nombre=nombre, apellido=apellido, bibliografia=bibliografia)
        else:
            autor.apellido = apellido
            autor.nombre = nombre
            autor.bibliografia = bibliografia
            autor.save()
        return redirect('lista_autores')
    context = {'autor': autor,
               'titulo': 'Editar Autor' if modo == 'editar' else 'Crear Autor',
               'texto_boton': 'Guardar cambios' if modo == 'editar' else 'Crear'}
    return render(request, 'gestion/templates/crear_autores.html', context)

def lista_multas(request):
    rol = obtener_rol(request.user)
    # Usuarios normales solo ven sus multas
    if request.user.is_authenticated and rol == 'usuario':
        multas = Multa.objects.filter(prestamo__usuario=request.user)
    else:
        multas = Multa.objects.all()
    return render(request, 'gestion/templates/multas.html', {'multas': multas})

@requiere_rol('bibliotecario', 'admin')
def crear_prestamo(request):
    libro = Libro.objects.filter(disponible=True)
    # Solo mostrar usuarios normales (no personal del sistema)
    usuario = User.objects.filter(perfil__rol='usuario')
    if request.method == 'POST':
        libro_id = request.POST.get('libro')
        usuario_id = request.POST.get('usuario')
        fecha_prestamo = request.POST.get('fecha_prestamo')
        fecha_max = request.POST.get('fecha_max')
        if libro_id and usuario_id and fecha_prestamo and fecha_max:
            libro = get_object_or_404(Libro, id=libro_id)
            usuario = get_object_or_404(User, id=usuario_id)
            
            # Verificar stock
            if libro.stock > 0:
                prestamo = Prestamo.objects.create(libro = libro,
                                                   usuario=usuario,
                                                   fecha_prestamos=fecha_prestamo,
                                                   fecha_max=fecha_max)
                
                # Actualizar stock y disponibilidad
                libro.stock -= 1
                libro.disponible = libro.stock > 0
                libro.save()
                
                # Registrar en log
                registrar_log(request.user, 'crear', f'Creó préstamo #{prestamo.pk} de "{libro.titulo}" para {usuario.username}', request, 'Prestamo', prestamo.pk)
                
                return redirect('detalle_prestamo', id=prestamo.pk)
            else:
                 # Manejo visual en caso de error (aunque el filtro inicial ayuda)
                 return render(request, 'gestion/templates/crear_prestamo.html', {
                    'libros': Libro.objects.filter(disponible=True), # Recargar
                    'usuarios': User.objects.filter(perfil__rol='usuario'),
                    'error': 'El libro seleccionado no tiene stock disponible.'
                 })
    fecha = (timezone.now().date()).isoformat() # YYYY-MM-DD este se captura l aparte de al fehc actual
    return render(request, 'gestion/templates/crear_prestamo.html', {'libros': libro,
                                                                     'usuarios': usuario,
                                                                     'fecha': fecha})

@requiere_rol('bodeguero')
def editar_autor(request, id):
    autor = get_object_or_404(Autor, id=id)
    if request.method == 'POST':
        nombre = request.POST.get('nombre')
        apellido = request.POST.get('apellido')
        bibliografia = request.POST.get('bibliografia')
        
        if nombre and apellido:
            autor.apellido = apellido
            autor.nombre = nombre
            autor.bibliografia = bibliografia
            autor.save()
            return redirect('lista_autores')
    
    return render(request, 'gestion/templates/editar_autor.html', {'autor': autor})

@requiere_rol('bodeguero')
def eliminar_autor(request, id):
    autor = get_object_or_404(Autor, id=id)
    
    if request.method == 'POST':
        try:
            autor.delete()
            registrar_log(request.user, 'eliminar', f'Eliminó autor: {autor.nombre} {autor.apellido}', request, 'Autor', id)
            return redirect('lista_autores')
        except:
            # Si tiene libros asociados, no se puede eliminar (por on_delete=PROTECT)
            return render(request, 'gestion/templates/autores.html', {
                'autores': Autor.objects.all(),
                'error': f'No se puede eliminar a {autor.nombre} {autor.apellido} porque tiene libros registrados.'
            })
    
    return redirect('lista_autores')

def detalle_autor(request, id):
    """Vista pública para ver detalles de un autor"""
    autor = get_object_or_404(Autor, id=id)
    libros = Libro.objects.filter(autor=autor)
    
    # Check permissions logic (Bodeguero manages)
    puede_gestionar = False
    if request.user.is_authenticated:
        rol = obtener_rol(request.user)
        puede_gestionar = rol in ['bodeguero', 'superusuario']
        
    return render(request, 'gestion/templates/detalle_autor.html', {
        'autor': autor,
        'libros': libros,
        'puede_gestionar': puede_gestionar
    })

# Códigos de verificación para roles especiales
CODIGOS_ROL = {
    'usuario': None,  # No requiere código
    'bodeguero': 'bodega76',
    'bibliotecario': 'biblio76',
    'admin': 'admin76',
    'superusuario': 'superuser76',
}

def registro(request):
    if request.method == 'POST':
        form = RegistroUsuarioForm(request.POST)
        if form.is_valid():
            rol_seleccionado = form.cleaned_data.get('rol')
            codigo_ingresado = form.cleaned_data.get('codigo_rol')
            codigo_requerido = CODIGOS_ROL.get(rol_seleccionado)
            
            # Validar código si el rol lo requiere
            if codigo_requerido is not None and codigo_ingresado != codigo_requerido:
                form.add_error('codigo_rol', f'Código incorrecto para el rol {rol_seleccionado}')
                return render(request, 'gestion/templates/registration/registro.html', {'form': form})
            
            usuario = form.save()  # guarda el usuario en la base de datos
            cedula = form.cleaned_data.get('cedula')
            telefono = form.cleaned_data.get('telefono')
            
            # Crear perfil con el rol seleccionado
            perfil = Perfil.objects.create(
                usuario=usuario,
                cedula=cedula,
                telefono=telefono,
                rol=rol_seleccionado
            )
            
            # Asignar is_staff a roles con privilegios
            if rol_seleccionado in ['bodeguero', 'bibliotecario', 'admin', 'superusuario']:
                usuario.is_staff = True
                usuario.save()
            
            # Registrar en logs
            registrar_log(usuario, 'registro', f'Nuevo usuario registrado: {usuario.username} con rol {rol_seleccionado}', request, 'User', usuario.id)
            
            login(request, usuario)
            return redirect('index')
    else:
        form = RegistroUsuarioForm() 
    return render(request, 'gestion/templates/registration/registro.html', {'form': form})

def detalle_prestamo(request, id):
    prestamo = get_object_or_404(Prestamo, id=id)
    multas = prestamo.multas.all()
    return render(request, 'gestion/templates/detalle_prestamo.html', {
        'prestamo': prestamo,
        'multas': multas
    })

@requiere_rol('bibliotecario', 'admin')
def crear_multa(request, prestamo_id):
    prestamo = get_object_or_404(Prestamo, id=prestamo_id)
    if request.method == 'POST':
        tipo = request.POST.get('tipo')
        monto = request.POST.get('monto', 0)
        if tipo:
            multa = Multa.objects.create(
                prestamo=prestamo,
                tipo=tipo,
                monto=monto
            )
            return redirect('detalle_prestamo', id=prestamo.pk)
    return render(request, 'gestion/templates/crear_multa.html', {'prestamo': prestamo})

@requiere_rol('bibliotecario', 'admin')
def devolver_libro(request, prestamo_id):
    prestamo = get_object_or_404(Prestamo, id=prestamo_id)

    if request.method == 'POST':
        estado_libro = request.POST.get('estado_libro')

        # Marcar fecha de devolución
        # Marcar fecha de devolución
        prestamo.fecha_devolucion = timezone.now().date()
        
        # Restaurar Stock
        prestamo.libro.stock += 1
        prestamo.libro.disponible = True
        prestamo.libro.save()
        
        prestamo.save()
        
        # Crear multa por retraso si hay días de retraso
        if prestamo.dias_retraso > 0:
            Multa.objects.create(
                prestamo=prestamo,
                tipo='r',
                monto=prestamo.multa_retraso
            )
        
        # Crear multa por estado del libro
        if estado_libro == 'deterioro':
            Multa.objects.create(prestamo=prestamo, tipo='d', monto=10.00)
        elif estado_libro == 'perdida':
            Multa.objects.create(prestamo=prestamo, tipo='p', monto=20.00)
        
        # Registrar en log
        registrar_log(request.user, 'editar', f'Devolvió libro "{prestamo.libro.titulo}" del préstamo #{prestamo.pk}. Estado: {estado_libro}', request, 'Prestamo', prestamo.pk)
        
        return redirect('detalle_prestamo', id=prestamo.pk)
    
    return redirect('detalle_prestamo', id=prestamo.pk)

@requiere_rol('bibliotecario', 'admin')
def pagar_multa(request, multa_id):
    multa = get_object_or_404(Multa, id=multa_id)
    multa.pagada = True
    multa.save()
    
    return redirect('detalle_prestamo', id=multa.prestamo.pk)

@requiere_rol('bibliotecario', 'admin')
def renovar_prestamo(request, prestamo_id):
    
    prestamo = get_object_or_404(Prestamo, id=prestamo_id)
    
    from datetime import timedelta
    prestamo.fecha_max = timezone.now().date() + timedelta(days=7)
    prestamo.save()
    
    return redirect('detalle_prestamo', id=prestamo.pk)

#API OPENLIBRARY
def api_buscar_libros(request):
    query = request.GET.get('q', '').strip()
    if not query: return JsonResponse({'libros': []})
    
    docs = buscar_libros(query)
    libros = []
    
    for doc in docs:
        descripcion = ''
        if doc.get('key'):
            try: 
                r = requests.get(f'https://openlibrary.org{doc.get("key")}.json', timeout=3)
                if r.status_code == 200:
                    d = r.json().get('description', '')
                    descripcion = d.get('value', '') if isinstance(d, dict) else d
            except: pass
        
        libros.append({
            'titulo': doc.get('title', 'Sin título'),
            'autor': ', '.join(doc.get('author_name', ['Desconocido'])),
            'año': doc.get('first_publish_year', 'N/A'),
            'portada': f"https://covers.openlibrary.org/b/id/{doc.get('cover_i')}-M.jpg" if doc.get('cover_i') else None,
            'descripcion': descripcion[:500],
            'id_openlibrary': doc.get('key')
        })
    return JsonResponse({'libros': libros})

def api_buscar_autores(request):
    query = request.GET.get('q', '').strip()
    if not query: return JsonResponse({'autores': []})
    
    docs = buscar_autores(query)
    autores = []
    
    for doc in docs:
        bio = ''
        if doc.get('key'):
            try:
                r = requests.get(f'https://openlibrary.org/authors/{doc.get("key")}.json', timeout=3)
                if r.status_code == 200:
                    b = r.json().get('bio', '')
                    bio = b.get('value', '') if isinstance(b, dict) else b
            except: pass
            
        autores.append({
            'nombre': doc.get('name', 'Sin nombre'),
            'obras': doc.get('work_count', 0),
            'biografia': bio[:500] 
        })
    return JsonResponse({'autores': autores})

# =====================================================
# SISTEMA DE SOLICITUDES DE PRÉSTAMOS
# =====================================================

@login_required
def crear_solicitud(request):
    """Vista para que usuarios normales soliciten un préstamo"""
    # Obtener libros disponibles
    libros_disponibles = Libro.objects.filter(disponible=True)
    
    if request.method == 'POST':
        libro_id = request.POST.get('libro')
        dias = request.POST.get('dias', 7)
        
        if libro_id:
            libro = get_object_or_404(Libro, id=libro_id)
            
            # Verificar que el libro esté disponible
            if not libro.disponible:
                return render(request, 'gestion/templates/crear_solicitud.html', {
                    'libros': libros_disponibles,
                    'error': 'Este libro ya no está disponible'
                })
            
            # Verificar que no tenga una solicitud pendiente para el mismo libro
            solicitud_existente = SolicitudPrestamo.objects.filter(
                usuario=request.user,
                libro=libro,
                estado='pendiente'
            ).exists()
            
            if solicitud_existente:
                return render(request, 'gestion/templates/crear_solicitud.html', {
                    'libros': libros_disponibles,
                    'error': 'Ya tienes una solicitud pendiente para este libro'
                })
            
            # Crear la solicitud
            solicitud = SolicitudPrestamo.objects.create(
                usuario=request.user,
                libro=libro,
                dias_solicitados=int(dias)
            )
            
            # Registrar en log
            registrar_log(request.user, 'crear', f'Solicitó préstamo del libro "{libro.titulo}" por {dias} días', request, 'SolicitudPrestamo', solicitud.pk)
            
            return redirect('mis_solicitudes')
    
    return render(request, 'gestion/templates/crear_solicitud.html', {
        'libros': libros_disponibles
    })

@login_required
def mis_solicitudes(request):
    """Vista para que el usuario vea sus solicitudes"""
    solicitudes = SolicitudPrestamo.objects.filter(usuario=request.user)
    return render(request, 'gestion/templates/mis_solicitudes.html', {
        'solicitudes': solicitudes
    })

@requiere_rol('bibliotecario', 'admin')
def lista_solicitudes(request):
    """Vista para que bibliotecarios/admins vean todas las solicitudes pendientes"""
    solicitudes_pendientes = SolicitudPrestamo.objects.filter(estado='pendiente')
    solicitudes_procesadas = SolicitudPrestamo.objects.exclude(estado='pendiente')[:20]
    
    return render(request, 'gestion/templates/lista_solicitudes.html', {
        'solicitudes_pendientes': solicitudes_pendientes,
        'solicitudes_procesadas': solicitudes_procesadas
    })

@requiere_rol('bibliotecario', 'admin')
def aprobar_solicitud(request, solicitud_id):
    """Vista para aprobar una solicitud y crear el préstamo"""
    solicitud = get_object_or_404(SolicitudPrestamo, id=solicitud_id)
    
    if solicitud.estado != 'pendiente':
        return redirect('lista_solicitudes')
    
    if request.method == 'POST':
        # Verificar que el libro sigue disponible
        # Verificar que hay STOCK disponible
        if solicitud.libro.stock <= 0:
            solicitud.estado = 'rechazada'
            solicitud.motivo_rechazo = 'No hay stock disponible'
            solicitud.fecha_respuesta = timezone.now()
            solicitud.respondido_por = request.user
            solicitud.save()
            return redirect('lista_solicitudes')
        
        # Aprobar la solicitud
        solicitud.estado = 'aprobada'
        solicitud.fecha_respuesta = timezone.now()
        solicitud.respondido_por = request.user
        solicitud.save()
        
        # Crear el préstamo
        fecha_max = timezone.now().date() + timedelta(days=solicitud.dias_solicitados)
        prestamo = Prestamo.objects.create(
            libro=solicitud.libro,
            usuario=solicitud.usuario,
            fecha_max=fecha_max
        )
        
        # Actualizar stock
        solicitud.libro.stock -= 1
        solicitud.libro.disponible = solicitud.libro.stock > 0
        solicitud.libro.save()
        
        # Registrar en log
        registrar_log(request.user, 'aprobar', f'Aprobó solicitud #{solicitud.pk} de {solicitud.usuario.username} para "{solicitud.libro.titulo}"', request, 'SolicitudPrestamo', solicitud.pk)
        
        return redirect('detalle_prestamo', id=prestamo.pk)
    
    return redirect('lista_solicitudes')

@requiere_rol('bibliotecario', 'admin')
def rechazar_solicitud(request, solicitud_id):
    """Vista para rechazar una solicitud"""
    solicitud = get_object_or_404(SolicitudPrestamo, id=solicitud_id)
    
    if solicitud.estado != 'pendiente':
        return redirect('lista_solicitudes')
    
    if request.method == 'POST':
        motivo = request.POST.get('motivo', 'Sin motivo especificado')
        
        solicitud.estado = 'rechazada'
        solicitud.motivo_rechazo = motivo
        solicitud.fecha_respuesta = timezone.now()
        solicitud.respondido_por = request.user
        solicitud.save()
        
        # Registrar en log
        registrar_log(request.user, 'rechazar', f'Rechazó solicitud #{solicitud.pk} de {solicitud.usuario.username} para "{solicitud.libro.titulo}". Motivo: {motivo}', request, 'SolicitudPrestamo', solicitud.pk)
    
    return redirect('lista_solicitudes')

# =====================================================
# GESTIÓN DE USUARIOS (Solo Admin y Superusuario)
# =====================================================

@requiere_rol('admin')
def lista_usuarios(request):
    """Vista para ver todos los usuarios del sistema"""
    usuarios = User.objects.all().select_related('perfil').order_by('-date_joined')
    return render(request, 'gestion/templates/lista_usuarios.html', {
        'usuarios': usuarios
    })

@requiere_rol('admin')
def crear_usuario(request):
    """Vista para crear un nuevo usuario (admin puede crear cualquier rol)"""
    if request.method == 'POST':
        form = RegistroUsuarioForm(request.POST)
        if form.is_valid():
            usuario = form.save()
            cedula = form.cleaned_data.get('cedula')
            telefono = form.cleaned_data.get('telefono')
            rol = form.cleaned_data.get('rol')
            
            # Admin puede crear cualquier rol sin código
            perfil = Perfil.objects.create(
                usuario=usuario,
                cedula=cedula,
                telefono=telefono,
                rol=rol
            )
            
            # Asignar is_staff según el rol
            if rol in ['bodeguero', 'bibliotecario', 'admin', 'superusuario']:
                usuario.is_staff = True
                usuario.save()
            
            return redirect('lista_usuarios')
    else:
        form = RegistroUsuarioForm()
    
    return render(request, 'gestion/templates/crear_usuario.html', {'form': form})

@requiere_rol('admin')
def editar_usuario(request, user_id):
    """Vista para editar el rol de un usuario"""
    usuario = get_object_or_404(User, id=user_id)
    
    # Obtener o crear perfil
    perfil, created = Perfil.objects.get_or_create(
        usuario=usuario,
        defaults={'cedula': '0000000000', 'telefono': '0000000000', 'rol': 'usuario'}
    )
    
    if request.method == 'POST':
        # Datos del usuario (User model)
        usuario.first_name = request.POST.get('first_name', usuario.first_name)
        usuario.last_name = request.POST.get('last_name', usuario.last_name)
        usuario.email = request.POST.get('email', usuario.email)
        
        # Datos del perfil
        nuevo_rol = request.POST.get('rol')
        nueva_cedula = request.POST.get('cedula', perfil.cedula)
        nuevo_telefono = request.POST.get('telefono', perfil.telefono)
        
        perfil.rol = nuevo_rol
        perfil.cedula = nueva_cedula
        perfil.telefono = nuevo_telefono
        perfil.save()
        
        # Actualizar is_staff según el rol
        if nuevo_rol in ['bodeguero', 'bibliotecario', 'admin', 'superusuario']:
            usuario.is_staff = True
        else:
            usuario.is_staff = False
        usuario.save()
        
        return redirect('lista_usuarios')
    
    roles = Perfil.ROLES
    return render(request, 'gestion/templates/editar_usuario.html', {
        'usuario': usuario,
        'perfil': perfil,
        'roles': roles
    })

@requiere_rol('admin')
def eliminar_usuario(request, user_id):
    """Vista para eliminar un usuario"""
    usuario = get_object_or_404(User, id=user_id)
    
    # No permitir eliminar al propio usuario
    if usuario == request.user:
        return redirect('lista_usuarios')
    
    if request.method == 'POST':
        username = usuario.username
        usuario.delete()
        registrar_log(request.user, 'eliminar', f'Eliminó al usuario: {username}', request, 'User')
    
    return redirect('lista_usuarios')


# =====================================================
# VISUALIZACIÓN DE LOGS (Solo Admin y Superusuario)
# =====================================================

@requiere_rol('admin')
def lista_logs(request):
    """Vista para ver todos los registros de actividad"""
    # Filtros
    tipo = request.GET.get('tipo', '')
    usuario_filtro = request.GET.get('usuario', '')
    fecha = request.GET.get('fecha', '')
    
    logs = RegistroActividad.objects.all()
    
    if tipo:
        logs = logs.filter(tipo_accion=tipo)
    if usuario_filtro:
        logs = logs.filter(usuario__username__icontains=usuario_filtro)
    if fecha:
        logs = logs.filter(fecha_hora__date=fecha)
    
    # Limitar a los últimos 500 registros
    logs = logs[:500]
    
    tipos_accion = RegistroActividad.TIPOS_ACCION
    
    return render(request, 'gestion/templates/lista_logs.html', {
        'logs': logs,
        'tipos_accion': tipos_accion,
        'filtro_tipo': tipo,
        'filtro_usuario': usuario_filtro,
        'filtro_fecha': fecha,
    })


# =====================================================
# GESTIÓN DE STOCK (Bodeguero)
# =====================================================

@requiere_rol('bodeguero', 'admin')
def gestionar_stock(request):
    """Vista para ver y editar el stock de libros"""
    libros = Libro.objects.all().order_by('titulo')
    rol = obtener_rol(request.user)
    puede_editar = rol == 'bodeguero' or rol == 'superusuario'
    
    if request.method == 'POST' and puede_editar:
        libro_id = request.POST.get('libro_id')
        nuevo_stock = request.POST.get('stock')
        
        if libro_id and nuevo_stock:
            libro = get_object_or_404(Libro, id=libro_id)
            libro.stock = int(nuevo_stock)
            libro.save()
            registrar_log(request.user, 'editar', f'Actualizó stock de "{libro.titulo}" a {nuevo_stock}', request, 'Libro', libro.pk)
    
    return render(request, 'gestion/templates/gestionar_stock.html', {
        'libros': libros,
        'puede_editar': puede_editar,
    })

