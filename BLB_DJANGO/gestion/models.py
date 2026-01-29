from django.db import models
from django.conf import settings
from django.utils import timezone
from django.contrib.auth.models import User

# Create your models here.

#clases
    #definir los campos para la clase con sus tipos (ejm: charfield, integerfield, datefield, booleanfield, etc)
    #para tipo texto usar (models.charfied) o texto largo (models.textfield)
    #atributos de charfield:
    # max_length=n para definir la longitud maxima,
    # blank=True, null=True (para que no sean obligatorios), y sean blancos o nulos
    # unique=True (para que no se repitan)

class Autor(models.Model):
    nombre = models.CharField(max_length=150)
    apellido = models.CharField(max_length=50)
    bibliografia = models.CharField(max_length=200, blank=True, null=True)
    
    def __str__(self):
        return f"{self.nombre} {self.apellido}"
    
class Libro(models.Model):
    titulo = models.CharField(max_length=200)
    autor = models.ForeignKey(Autor, related_name="libros", on_delete=models.PROTECT)
    descripcion = models.TextField(blank=True, null=True)
    disponible = models.BooleanField(default=True)
    imagen = models.ImageField(upload_to='libros/', blank=True, null=True)
    stock = models.IntegerField(default=1)
    anio_publicacion = models.IntegerField(blank=True, null=True)
    es_de_openlibrary = models.BooleanField(default=False)
    
    def __str__(self):
        return f"{self.titulo} - {self.autor.nombre} {self.autor.apellido}"
    
class Prestamo(models.Model):
    libro = models.ForeignKey(Libro, related_name="prestamos", on_delete=models.PROTECT)
    usuario = models.ForeignKey(settings.AUTH_USER_MODEL, related_name="prestamos", on_delete=models.PROTECT)
    fecha_prestamos = models.DateField(default=timezone.now)
    fecha_max = models.DateField()
    fecha_devolucion = models.DateField(blank=True, null=True)
    
    class Meta:
        permissions = (
            ("Ver_prestamos", "Puede ver prestamos"),
            ("gestionar_prestamos", "Puede gestionar prestamos"),
        )
    
    def __str__(self):
        return f"prestamo de {self.libro} a {self.usuario}"
    
# funciones para calcular dias de retraso y multa por retraso

    #Calcular dias de retraso
    @property #con el property estamos definiendo que esta funcion se va a comportar como un atributo
    def dias_retraso(self):
        hoy = timezone.now().date() #fecha actual
        fecha_ref = self.fecha_devolucion or hoy #si la fecha de devolucion es nula se toma la fecha actual
        if fecha_ref >= self.fecha_max: #si la fecha de referencia es mayor a la fecha maxima
            return (fecha_ref - self.fecha_max).days #retorna la diferencia en dias entre la fecha de referencia y la fecha maxima
        else:
            return 0 #si no hay retraso retorna 0 dias de retraso

    #calcular multa por retraso
    @property
    def multa_retraso(self):
        tarifa = 2.00
        return self.dias_retraso * tarifa 
    #retorna la multa por retraso, multiplicando los dias de retraso por la tarifa

class Multa(models.Model):
    prestamo = models.ForeignKey(Prestamo, related_name="multas", on_delete=models.PROTECT)
    tipo = models.CharField(max_length=10, choices=(('r', 'retraso'),
                                                    ('p', 'perdida'),
                                                    ('d','deterioro')))
    #con choices definimos las opciones que puede tener el campo tipo
    monto = models.DecimalField(max_digits=6, decimal_places=2, default=0)
    #DecimalField se 
    pagada = models.BooleanField(default=False) #para ver si esta pagado o no pagado
    fecha = models.DateField(default=timezone.now) #fecha a la que se crea la multa ,por defecto la fecha actual

    def __str__(self):
        return f"Multa {self.tipo} - {self.monto} - {self.prestamo}"
    
    def save(self, *args, **kwargs):
        if self.tipo == 'r' and self.monto == 0:
            self.monto = self.prestamo.multa_retraso
        super().save(*args, **kwargs)

        
# =====================================================
# SISTEMA DE SOLICITUDES DE PRÉSTAMOS
# =====================================================
# Los usuarios normales pueden solicitar préstamos
# Los bibliotecarios y admins pueden aprobar/rechazar

class SolicitudPrestamo(models.Model):
    ESTADOS = (
        ('pendiente', 'Pendiente'),
        ('aprobada', 'Aprobada'),
        ('rechazada', 'Rechazada'),
    )
    
    usuario = models.ForeignKey(settings.AUTH_USER_MODEL, related_name="solicitudes", on_delete=models.CASCADE)
    libro = models.ForeignKey(Libro, related_name="solicitudes", on_delete=models.PROTECT)
    dias_solicitados = models.IntegerField(default=7)  # Cuántos días quiere el libro
    fecha_solicitud = models.DateTimeField(default=timezone.now)
    estado = models.CharField(max_length=15, choices=ESTADOS, default='pendiente')
    fecha_respuesta = models.DateTimeField(blank=True, null=True)
    respondido_por = models.ForeignKey(settings.AUTH_USER_MODEL, related_name="solicitudes_respondidas", 
                                        on_delete=models.SET_NULL, blank=True, null=True)
    motivo_rechazo = models.TextField(blank=True, null=True)
    
    def __str__(self):
        return f"Solicitud de {self.usuario.username} - {self.libro.titulo} ({self.get_estado_display()})"
    
    class Meta:
        ordering = ['-fecha_solicitud']  # Las más recientes primero


class Perfil(models.Model):
    ROLES = (
        ('usuario', 'Usuario Normal'),
        ('bodeguero', 'Bodeguero'),
        ('bibliotecario', 'Bibliotecario'),
        ('admin', 'Administrador'),
        ('superusuario', 'Superusuario'),
    )
    
    usuario = models.OneToOneField(User, on_delete=models.CASCADE)
    cedula = models.CharField(max_length=13)
    telefono = models.CharField(max_length=10)
    rol = models.CharField(max_length=20, choices=ROLES, default='usuario')
    
    def __str__(self):
        return f"{self.usuario.username} - {self.get_rol_display()}"


# =====================================================
# SISTEMA DE LOGS / REGISTRO DE ACTIVIDAD
# =====================================================
class RegistroActividad(models.Model):
    TIPOS_ACCION = (
        ('login', 'Inicio de Sesión'),
        ('logout', 'Cierre de Sesión'),
        ('registro', 'Registro de Usuario'),
        ('crear', 'Crear'),
        ('editar', 'Editar'),
        ('eliminar', 'Eliminar'),
        ('ver', 'Ver/Consultar'),
        ('solicitud', 'Solicitud de Préstamo'),
        ('aprobar', 'Aprobar'),
        ('rechazar', 'Rechazar'),
        ('devolucion', 'Devolución'),
        ('pago', 'Pago de Multa'),
        ('otro', 'Otra Acción'),
    )
    
    usuario = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True)
    fecha_hora = models.DateTimeField(default=timezone.now)
    tipo_accion = models.CharField(max_length=20, choices=TIPOS_ACCION)
    descripcion = models.TextField()
    direccion_ip = models.GenericIPAddressField(null=True, blank=True)
    url = models.CharField(max_length=500, blank=True, null=True)
    modelo_afectado = models.CharField(max_length=100, blank=True, null=True)
    objeto_id = models.IntegerField(null=True, blank=True)
    
    class Meta:
        ordering = ['-fecha_hora']
        verbose_name = 'Registro de Actividad'
        verbose_name_plural = 'Registros de Actividad'
    
    def __str__(self):
        usuario_str = self.usuario.username if self.usuario else 'Anónimo'
        return f"{self.fecha_hora.strftime('%d/%m/%Y %H:%M')} - {usuario_str} - {self.get_tipo_accion_display()}"


def registrar_log(usuario, tipo_accion, descripcion, request=None, modelo=None, objeto_id=None):
    """
    Función auxiliar para registrar una actividad en el log.
    Uso: registrar_log(request.user, 'crear', 'Creó el libro: El Quijote', request, 'Libro', 1)
    Guarda en la base de datos Y en el archivo logs.txt
    """
    import os
    from datetime import datetime
    
    ip = None
    url = None
    
    if request:
        # Obtener IP del cliente
        x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
        if x_forwarded_for:
            ip = x_forwarded_for.split(',')[0]
        else:
            ip = request.META.get('REMOTE_ADDR')
        url = request.path
    
    # Guardar en base de datos
    RegistroActividad.objects.create(
        usuario=usuario if usuario and usuario.is_authenticated else None,
        tipo_accion=tipo_accion,
        descripcion=descripcion,
        direccion_ip=ip,
        url=url,
        modelo_afectado=modelo,
        objeto_id=objeto_id
    )
    
    # Guardar en archivo de texto
    try:
        # Ruta al archivo de logs
        base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        logs_file = os.path.join(base_dir, 'docs_utiles', 'logs.txt')
        
        # Formatear la línea de log
        fecha_hora = datetime.now().strftime('%d/%m/%Y %H:%M:%S')
        usuario_str = usuario.username if usuario and hasattr(usuario, 'username') else 'Anónimo'
        linea_log = f"[{fecha_hora}] | Usuario: {usuario_str} | Acción: {tipo_accion.upper()} | {descripcion} | IP: {ip or '-'} | URL: {url or '-'}\n"
        
        # Escribir al archivo (append mode)
        with open(logs_file, 'a', encoding='utf-8') as f:
            f.write(linea_log)
    except Exception as e:
        # Si falla la escritura al archivo, no interrumpir el flujo
        pass