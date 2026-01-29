from django.test import TestCase
from gestion.models import Autor, Libro, Prestamo
from django.contrib.auth.models import User
from django.utils import timezone
from django.urls import reverse


class LibroModelTest(TestCase):
    @classmethod
    def setUpTestData(cls):
        # Crear un autor para usar en las pruebas
        autor = Autor.objects.create(nombre="Isaac", apellido="Asimov", bibliografia="Escritor de ciencia ficción")
        Libro.objects.create(titulo="Fundacion", autor=autor, disponible= True)
        
    def test_str_devuelve_titulo(self):
        libro = Libro.objects.get(id=1) #obtener el el id que estoy creando en setuptestdata
        self.assertEqual(str(libro), 'Fundacion') #verificar que el str del libro devuelva el titulo

class PrestamoModelTest(TestCase):
    @classmethod
    def setUpTestData(cls):
        usuario = User.objects.create_user(username='testuser', password='12345678') #crear un usuario de prueba
        Libro.objects.create(titulo="I Robot", autor=1, disponible=False) #crear un libro no disponible
        cls.prestamo = Prestamo.objects.create( #el cls es para definir atributos de la clase de prueba parecido al self
            libro=Libro,
            usuario=usuario,
            fecha_max='2025-12-25'
        )
        
    def test_libro_no_disponible(self):
        self.prestamo.refresh_from_db()  # Actualizar el objeto desde la base de datos
        self.assertFalse(self.prestamo.libro) # Verificar que el libro no esté disponible
        self.assertEqual(self.prestamo.dias_retraso, 8)  # Verificar el título del libro
        if self.prestamo.dias_retraso > 0:
            self.assertGreater(self.prestamo.multa_restraso, 1000)  # Verificar la multa por retraso
            
class PrestamoUsuarioViewTest(TestCase):
    def setUp(self):
        self.user1 = User.objects.create_user('u1', password='test12345')
        self.user2 = User.objects.create_user('u2', password='test12345')
        
    def test_redirige_no_login(self):
        resp = self.client.get(reverse('crear_autores'))
        self.assertEqual(resp.status_code, 302)  # Redirige al login
        
    def test_carga_login(self):
        resp = self.client.login(username=1, password="test12345")
        self.assertEqual(resp.status_code, 200)
        respl = self.client.get(reverse('crear_autores'))
        self.assertEqual(respl.status_code, 200)

           
#aprender sobre los codigos de estado de respuesta HTTP

#conetcar el opne libraruy
#validaciones 
#y test de todos