from django.contrib.auth.models import AbstractUser
from django.db import models


class User(AbstractUser):
    class Roles(models.TextChoices):
        DUENA = "DUEÑA", "Dueña"
        PROFESIONAL = "PROFESIONAL", "Profesional"

    rol = models.CharField(max_length=20, choices=Roles.choices)
    habilitado = models.BooleanField(default=True)


class Consultorio(models.Model):
    nombre = models.CharField(max_length=100)
    numero = models.IntegerField(unique=True)

    def __str__(self):
        return f"{self.nombre} ({self.numero})"


class Paciente(models.Model):
    nombre_completo = models.CharField(max_length=255)
    dni = models.CharField(max_length=50, unique=True)
    fecha_nacimiento = models.DateField(null=True, blank=True)
    email = models.EmailField(null=True, blank=True)
    telefono = models.CharField(max_length=50, null=True, blank=True)
    obra_social = models.CharField(max_length=255, null=True, blank=True)
    numero_afiliado = models.CharField(max_length=100, null=True, blank=True)
    diagnostico = models.TextField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.nombre_completo


class Turno(models.Model):
    class Estados(models.TextChoices):
        CONFIRMADO = "CONFIRMADO", "Confirmado"
        EN_ESPERA = "EN_ESPERA", "En espera"
        FINALIZADO = "FINALIZADO", "Finalizado"
        CANCELADO = "CANCELADO", "Cancelado"

    paciente = models.ForeignKey(
        Paciente, on_delete=models.CASCADE, related_name="turnos"
    )
    profesional = models.ForeignKey(
        User, on_delete=models.CASCADE, related_name="turnos"
    )
    consultorio = models.ForeignKey(
        Consultorio, on_delete=models.CASCADE, related_name="turnos"
    )
    inicio = models.DateTimeField()
    fin = models.DateTimeField()
    estado = models.CharField(max_length=20, choices=Estados.choices)

    class Meta:
        unique_together = ("consultorio", "inicio")


class Evolucion(models.Model):
    paciente = models.ForeignKey(
        Paciente, on_delete=models.CASCADE, related_name="evoluciones"
    )
    profesional = models.ForeignKey(
        User, on_delete=models.CASCADE, related_name="evoluciones"
    )
    texto = models.TextField()
    creado_en = models.DateTimeField(auto_now_add=True)


class Documento(models.Model):
    paciente = models.ForeignKey(
        Paciente, on_delete=models.CASCADE, related_name="documentos"
    )
    nombre = models.CharField(max_length=255)
    archivo = models.FileField(upload_to="documentos/")
    creado_en = models.DateTimeField(auto_now_add=True)
