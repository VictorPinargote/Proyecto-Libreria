from django import forms
from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth.models import User

#clase para crear un formulario de registro
class RegistroUsuarioForm(UserCreationForm):
    #campos de que se llaman de el modelo User
    first_name = forms.CharField(max_length=50, required=True)
    last_name = forms.CharField(max_length=50, required=True)
    email = forms.EmailField(required=True)

    #campos que se llaman del model perfil
    cedula = forms.CharField(max_length=13, required=True)
    telefono = forms.CharField(max_length=10, required=True)

    #campo para seleccionar rol
    rol = forms.ChoiceField(choices=[
        ('usuario', 'Usuario Normal'),
        ('bodeguero', 'Bodeguero'),
        ('bibliotecario', 'Bibliotecario'),
        ('admin', 'Administrador'),
        ('superusuario', 'Superusuario'),
    ], required=True, initial='usuario')
    
    #código de verificación para roles especiales
    codigo_rol = forms.CharField(max_length=25, required=False, widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Ingresa el código de verificación'}))

    class Meta:
        model = User
        fields = ['username', 'first_name', 'last_name', 'email']
    