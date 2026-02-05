from django.contrib.auth import authenticate
from rest_framework_simplejwt.serializers import TokenObtainPairSerializer
from rest_framework import exceptions
from rest_framework import serializers
from django.utils import timezone
from .models import (
    User,
    Paciente,
    Consultorio,
    Turno,
    Evolucion,
    Documento,
    Informe,
    Invitacion,
    AuditLog,
)


class LoginSerializer(serializers.Serializer):
    email = serializers.EmailField()
    password = serializers.CharField(write_only=True)

    def validate(self, attrs):
        email = (attrs.get("email") or "").strip().lower()
        password = attrs.get("password")

        if email and password:
            # authenticate puede recibir username o el campo USERNAME_FIELD
            user = authenticate(username=email, password=password)

            if not user:
                raise serializers.ValidationError(
                    "Credenciales inválidas.",
                    code="authorization",
                )

            if not user.is_enabled:
                raise serializers.ValidationError(
                    "Su usuario no está habilitado. Contacte a la administración.",
                    code="disabled",
                )

            if not user.is_active:
                raise serializers.ValidationError(
                    "La cuenta está desactivada.",
                    code="inactive",
                )

            attrs["user"] = user
            return attrs

        raise serializers.ValidationError(
            "Debe enviar email y contraseña.",
            code="authorization",
        )


class CustomTokenObtainPairSerializer(TokenObtainPairSerializer):
    def validate(self, attrs):
        email = (attrs.get("email") or "").strip().lower()
        attrs["email"] = email
        data = super().validate(attrs)

        user = self.user  # usuario autenticado

        if not user.is_enabled:
            raise exceptions.AuthenticationFailed(
                "Su usuario no está habilitado. Contacte a la administración.",
                code="disabled",
            )

        if not user.is_active:
            raise exceptions.AuthenticationFailed(
                "La cuenta está desactivada.",
                code="inactive",
            )

        # Devolvemos también datos útiles para el front
        data.update(
            {
                "user": {
                    "id": user.id,
                    "email": user.email,
                    "first_name": user.first_name,
                    "last_name": user.last_name,
                    "role": user.role,
                }
            }
        )

        AuditLog.objects.create(
            actor=user,
            action=AuditLog.Action.LOGIN,
            target_type="User",
            target_id=str(user.id),
            metadata={"email": user.email},
        )

        return data

    @classmethod
    def get_token(cls, user):
        token = super().get_token(user)
        # Info extra en el payload del token
        token["role"] = user.role
        token["email"] = user.email
        return token


class PacienteSerializer(serializers.ModelSerializer):
    class Meta:
        model = Paciente
        fields = [
            "id",
            "nombre_completo",
            "dni",
            "fecha_nacimiento",
            "email",
            "telefono",
            "obra_social",
            "numero_afiliado",
            "diagnostico",
            "created_at",
            "updated_at",
            "is_active",
            "deleted_at",
            "deleted_by",
        ]
        read_only_fields = ["is_active", "deleted_at", "deleted_by"]


class UserSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True, required=False)

    class Meta:
        model = User
        fields = [
            "id",
            "email",
            "first_name",
            "last_name",
            "role",
            "is_enabled",
            "is_active",
            "deleted_at",
            "deleted_by",
            "password",
        ]
        read_only_fields = ["deleted_at", "deleted_by"]

    def create(self, validated_data):
        password = validated_data.pop("password", None)
        return User.objects.create_user(password=password, **validated_data)

    def update(self, instance, validated_data):
        password = validated_data.pop("password", None)
        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        if password:
            instance.set_password(password)
        instance.save()
        return instance


class ConsultorioSerializer(serializers.ModelSerializer):
    class Meta:
        model = Consultorio
        fields = ["id", "nombre", "numero", "is_active", "deleted_at", "deleted_by"]
        read_only_fields = ["is_active", "deleted_at", "deleted_by"]

    def validate_numero(self, value):
        if value < 1 or value > 8:
            raise serializers.ValidationError(
                "El número de consultorio debe estar entre 1 y 8."
            )
        return value


class TurnoSerializer(serializers.ModelSerializer):
    class Meta:
        model = Turno
        fields = [
            "id",
            "paciente",
            "profesional",
            "consultorio",
            "inicio",
            "fin",
            "estado",
            "is_active",
            "deleted_at",
            "deleted_by",
        ]
        read_only_fields = ["profesional", "is_active", "deleted_at", "deleted_by"]

    def validate(self, attrs):
        inicio = attrs.get("inicio")
        fin = attrs.get("fin")
        consultorio = attrs.get("consultorio")

        if inicio and fin and fin <= inicio:
            raise serializers.ValidationError(
                {"fin": "La fecha y hora de fin debe ser posterior al inicio."}
            )

        if inicio and inicio.weekday() > 4:
            raise serializers.ValidationError(
                {"inicio": "Solo se permiten turnos de lunes a viernes."}
            )

        if inicio and fin:
            inicio_local = timezone.localtime(inicio)
            fin_local = timezone.localtime(fin)
            if inicio_local.minute not in (0, 30) or fin_local.minute not in (0, 30):
                raise serializers.ValidationError(
                    "Los turnos deben iniciar y finalizar en intervalos de 30 minutos."
                )
            if not (8 <= inicio_local.hour <= 17):
                raise serializers.ValidationError(
                    {"inicio": "El horario de inicio debe estar entre 08:00 y 17:30."}
                )
            if not (8 <= fin_local.hour <= 18):
                raise serializers.ValidationError(
                    {"fin": "El horario de fin debe estar entre 08:30 y 18:00."}
                )
            if fin_local.hour == 18 and fin_local.minute != 0:
                raise serializers.ValidationError(
                    {"fin": "El horario de fin máximo es 18:00."}
                )
            duration_seconds = (fin - inicio).total_seconds()
            if duration_seconds % (30 * 60) != 0:
                raise serializers.ValidationError(
                    "La duración del turno debe ser múltiplo de 30 minutos."
                )

        if inicio and fin and consultorio:
            qs = Turno.objects.filter(
                consultorio=consultorio,
                inicio__lt=fin,
                fin__gt=inicio,
            )
            if self.instance:
                qs = qs.exclude(pk=self.instance.pk)
            if qs.exists():
                raise serializers.ValidationError(
                    "El consultorio no está disponible en ese horario."
                )

        return attrs


class EvolucionSerializer(serializers.ModelSerializer):
    profesional_email = serializers.SerializerMethodField()
    profesional_nombre = serializers.SerializerMethodField()

    class Meta:
        model = Evolucion
        fields = [
            "id",
            "paciente",
            "profesional",
            "profesional_email",
            "profesional_nombre",
            "texto",
            "creado_en",
            "is_active",
            "deleted_at",
            "deleted_by",
        ]
        read_only_fields = [
            "profesional",
            "creado_en",
            "is_active",
            "deleted_at",
            "deleted_by",
        ]

    def get_profesional_email(self, obj):
        return getattr(obj.profesional, "email", None)

    def get_profesional_nombre(self, obj):
        first = getattr(obj.profesional, "first_name", "") or ""
        last = getattr(obj.profesional, "last_name", "") or ""
        nombre = f"{first} {last}".strip()
        return nombre or None


class DocumentoSerializer(serializers.ModelSerializer):
    class Meta:
        model = Documento
        fields = [
            "id",
            "paciente",
            "nombre",
            "archivo",
            "creado_en",
            "is_active",
            "deleted_at",
            "deleted_by",
        ]
        read_only_fields = ["creado_en", "is_active", "deleted_at", "deleted_by"]


class InformeSerializer(serializers.ModelSerializer):
    profesional_email = serializers.SerializerMethodField()
    profesional_nombre = serializers.SerializerMethodField()

    class Meta:
        model = Informe
        fields = [
            "id",
            "paciente",
            "profesional",
            "profesional_email",
            "profesional_nombre",
            "titulo",
            "contenido_html",
            "creado_en",
            "actualizado_en",
            "is_active",
            "deleted_at",
            "deleted_by",
        ]
        read_only_fields = [
            "profesional",
            "creado_en",
            "actualizado_en",
            "is_active",
            "deleted_at",
            "deleted_by",
        ]

    def get_profesional_email(self, obj):
        return getattr(obj.profesional, "email", None)

    def get_profesional_nombre(self, obj):
        first = getattr(obj.profesional, "first_name", "") or ""
        last = getattr(obj.profesional, "last_name", "") or ""
        nombre = f"{first} {last}".strip()
        return nombre or None


class InvitacionSerializer(serializers.ModelSerializer):
    class Meta:
        model = Invitacion
        fields = [
            "id",
            "email",
            "role",
            "token",
            "creado_en",
            "expira_en",
            "usado_en",
        ]
        read_only_fields = ["token", "creado_en", "expira_en", "usado_en"]


class ProfileSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ["id", "email", "first_name", "last_name", "role", "is_enabled"]
        read_only_fields = ["role", "is_enabled"]


class ChangePasswordSerializer(serializers.Serializer):
    new_password = serializers.CharField(min_length=8)


class AuditLogSerializer(serializers.ModelSerializer):
    actor_email = serializers.SerializerMethodField()

    class Meta:
        model = AuditLog
        fields = [
            "id",
            "actor",
            "actor_email",
            "action",
            "target_type",
            "target_id",
            "metadata",
            "created_at",
        ]

    def get_actor_email(self, obj):
        return getattr(obj.actor, "email", None)