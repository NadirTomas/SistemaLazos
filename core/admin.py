from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from .models import User, Consultorio, Paciente, Turno, Evolucion, Documento, Informe, Invitacion, AuditLog


@admin.register(User)
class UserAdmin(BaseUserAdmin):
    ordering = ("email",)
    list_display = (
        "email",
        "first_name",
        "last_name",
        "role",
        "is_enabled",
        "is_active",
        "deleted_at",
        "deleted_by",
    )
    list_filter = ("role", "is_enabled", "is_active")
    search_fields = ("email", "first_name", "last_name")

    fieldsets = (
        (None, {"fields": ("email", "password")}),
        ("Información personal", {"fields": ("first_name", "last_name")}),
        ("Rol y acceso", {"fields": ("role", "is_enabled")}),
        (
            "Permisos Django",
            {
                "fields": (
                    "is_active",
                    "is_staff",
                    "is_superuser",
                    "groups",
                    "user_permissions",
                )
            },
        ),
        ("Fechas", {"fields": ("last_login", "date_joined")}),
    )

    add_fieldsets = (
        (
            None,
            {
                "classes": ("wide",),
                "fields": (
                    "email",
                    "password1",
                    "password2",
                    "role",
                    "is_enabled",
                    "is_staff",
                ),
            },
        ),
    )

    filter_horizontal = ("groups", "user_permissions")


@admin.register(Consultorio)
class ConsultorioAdmin(admin.ModelAdmin):
    list_display = ("nombre", "numero", "is_active", "deleted_at", "deleted_by")
    search_fields = ("nombre",)
    ordering = ("numero",)


@admin.register(Paciente)
class PacienteAdmin(admin.ModelAdmin):
    list_display = (
        "nombre_completo",
        "dni",
        "email",
        "telefono",
        "is_active",
        "deleted_at",
        "deleted_by",
    )
    search_fields = ("nombre_completo", "dni", "email")
    ordering = ("nombre_completo",)


@admin.register(Turno)
class TurnoAdmin(admin.ModelAdmin):
    list_display = (
        "paciente",
        "profesional",
        "consultorio",
        "inicio",
        "fin",
        "estado",
        "is_active",
        "deleted_at",
        "deleted_by",
    )
    list_filter = ("estado", "consultorio", "is_active")
    search_fields = ("paciente__nombre_completo", "profesional__email")
    ordering = ("inicio",)


@admin.register(Evolucion)
class EvolucionAdmin(admin.ModelAdmin):
    list_display = ("paciente", "profesional", "creado_en", "is_active", "deleted_at", "deleted_by")
    search_fields = ("paciente__nombre_completo", "profesional__email")
    ordering = ("-creado_en",)


@admin.register(Documento)
class DocumentoAdmin(admin.ModelAdmin):
    list_display = ("paciente", "nombre", "creado_en", "is_active", "deleted_at", "deleted_by")
    search_fields = ("paciente__nombre_completo", "nombre")
    ordering = ("-creado_en",)


@admin.register(Informe)
class InformeAdmin(admin.ModelAdmin):
    list_display = ("paciente", "profesional", "titulo", "actualizado_en", "is_active", "deleted_at", "deleted_by")
    search_fields = ("paciente__nombre_completo", "profesional__email", "titulo")
    ordering = ("-actualizado_en",)


@admin.register(Invitacion)
class InvitacionAdmin(admin.ModelAdmin):
    list_display = ("email", "role", "creado_en", "expira_en", "usado_en")
    search_fields = ("email",)
    ordering = ("-creado_en",)


@admin.register(AuditLog)
class AuditLogAdmin(admin.ModelAdmin):
    list_display = ("created_at", "actor", "action", "target_type", "target_id")
    list_filter = ("action", "target_type")
    search_fields = ("actor__email", "target_id")
    ordering = ("-created_at",)
