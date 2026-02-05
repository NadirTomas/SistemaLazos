from django.db import models
from django.conf import settings
from django.contrib.auth.models import (
    AbstractBaseUser,
    PermissionsMixin,
    BaseUserManager,
)
from django.utils import timezone


class UserManager(BaseUserManager):
    def create_user(self, email, password=None, **extra_fields):
        if not email:
            raise ValueError("El usuario debe tener un email")

        email = (email or "").strip().lower()
        user = self.model(email=email, **extra_fields)
        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_superuser(self, email, password=None, **extra_fields):
        extra_fields.setdefault("is_staff", True)
        extra_fields.setdefault("is_superuser", True)
        extra_fields.setdefault("is_enabled", True)
        extra_fields.setdefault("role", User.Role.DUENA)

        if extra_fields.get("is_staff") is not True:
            raise ValueError("El superusuario debe tener is_staff=True")

        if extra_fields.get("is_superuser") is not True:
            raise ValueError("El superusuario debe tener is_superuser=True")

        return self.create_user(email, password, **extra_fields)


class SoftDeleteModel(models.Model):
    is_active = models.BooleanField(default=True)
    deleted_at = models.DateTimeField(null=True, blank=True)
    deleted_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="deleted_%(class)s_set",
    )

    class Meta:
        abstract = True

    def soft_delete(self, user=None):
        self.is_active = False
        self.deleted_at = timezone.now()
        if user is not None:
            self.deleted_by = user
        self.save(update_fields=["is_active", "deleted_at", "deleted_by"])


class User(AbstractBaseUser, PermissionsMixin):
    class Role(models.TextChoices):
        DUENA = "DUENA", "Dueña"
        PROFESIONAL = "PROFESIONAL", "Profesional"

    email = models.EmailField(unique=True)
    first_name = models.CharField(max_length=150, blank=True)
    last_name = models.CharField(max_length=150, blank=True)

    role = models.CharField(
        max_length=20,
        choices=Role.choices,
        default=Role.PROFESIONAL,
    )

    is_enabled = models.BooleanField(default=False)

    is_active = models.BooleanField(default=True)
    deleted_at = models.DateTimeField(null=True, blank=True)
    deleted_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="deleted_user_set",
    )
    is_staff = models.BooleanField(default=False)

    date_joined = models.DateTimeField(default=timezone.now)

    objects = UserManager()

    USERNAME_FIELD = "email"
    REQUIRED_FIELDS = []

    def __str__(self):
        return self.email

    def save(self, *args, **kwargs):
        if self.email:
            self.email = self.email.strip().lower()
        super().save(*args, **kwargs)

    def soft_delete(self, user=None):
        self.is_active = False
        self.deleted_at = timezone.now()
        if user is not None:
            self.deleted_by = user
        self.save(update_fields=["is_active", "deleted_at", "deleted_by"])


class Consultorio(SoftDeleteModel):
    nombre = models.CharField(max_length=100)
    numero = models.IntegerField(unique=True)

    def __str__(self):
        return f"{self.nombre} ({self.numero})"


class Paciente(SoftDeleteModel):
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


class Turno(SoftDeleteModel):
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


class Evolucion(SoftDeleteModel):
    paciente = models.ForeignKey(
        Paciente, on_delete=models.CASCADE, related_name="evoluciones"
    )
    profesional = models.ForeignKey(
        User, on_delete=models.CASCADE, related_name="evoluciones"
    )
    texto = models.TextField()
    creado_en = models.DateTimeField(auto_now_add=True)


class Documento(SoftDeleteModel):
    paciente = models.ForeignKey(
        Paciente, on_delete=models.CASCADE, related_name="documentos"
    )
    nombre = models.CharField(max_length=255)
    archivo = models.FileField(upload_to="documentos/")
    creado_en = models.DateTimeField(auto_now_add=True)


class Informe(SoftDeleteModel):
    paciente = models.ForeignKey(
        Paciente, on_delete=models.CASCADE, related_name="informes"
    )
    profesional = models.ForeignKey(
        User, on_delete=models.CASCADE, related_name="informes"
    )
    titulo = models.CharField(max_length=255)
    contenido_html = models.TextField()
    creado_en = models.DateTimeField(auto_now_add=True)
    actualizado_en = models.DateTimeField(auto_now=True)


class Invitacion(models.Model):
    email = models.EmailField()
    token = models.CharField(max_length=64, unique=True)
    role = models.CharField(
        max_length=20,
        choices=User.Role.choices,
        default=User.Role.PROFESIONAL,
    )
    creado_por = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="invitaciones_creadas",
    )
    creado_en = models.DateTimeField(auto_now_add=True)
    expira_en = models.DateTimeField()
    usado_en = models.DateTimeField(null=True, blank=True)

    def __str__(self):
        return f"{self.email} ({self.role})"


class AuditLog(models.Model):
    class Action(models.TextChoices):
        CREATE = "CREATE", "Crear"
        UPDATE = "UPDATE", "Actualizar"
        DELETE = "DELETE", "Eliminar"
        LOGIN = "LOGIN", "Login"
        PASSWORD_CHANGE = "PASSWORD_CHANGE", "Cambio de contraseña"
        INVITE_ACCEPT = "INVITE_ACCEPT", "Acepta invitación"

    actor = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="audit_logs",
    )
    action = models.CharField(max_length=30, choices=Action.choices)
    target_type = models.CharField(max_length=100)
    target_id = models.CharField(max_length=100, null=True, blank=True)
    metadata = models.JSONField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.action} {self.target_type} {self.target_id}"
