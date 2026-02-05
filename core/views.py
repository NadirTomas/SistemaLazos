from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status, viewsets, permissions
from rest_framework_simplejwt.views import TokenObtainPairView
from django.utils.dateparse import parse_date, parse_datetime
from django.utils import timezone
from django.conf import settings
from django.core.mail import send_mail
from django.utils.crypto import get_random_string
from .serializers import (
    LoginSerializer,
    CustomTokenObtainPairSerializer,
    PacienteSerializer,
    UserSerializer,
    ConsultorioSerializer,
    TurnoSerializer,
    EvolucionSerializer,
    DocumentoSerializer,
    InformeSerializer,
    InvitacionSerializer,
    ProfileSerializer,
    ChangePasswordSerializer,
    AuditLogSerializer,
)
from .models import (
    Paciente,
    User,
    Consultorio,
    Turno,
    Evolucion,
    Documento,
    Informe,
    Invitacion,
    AuditLog,
)
from .permissions import IsDuena, IsDuenaOrReadOnly


def log_action(actor, action, instance, metadata=None):
    AuditLog.objects.create(
        actor=actor,
        action=action,
        target_type=instance.__class__.__name__,
        target_id=str(getattr(instance, "id", "")),
        metadata=metadata or {},
    )


def soft_delete_instance(instance, user):
    instance.is_active = False
    instance.deleted_at = timezone.now()
    instance.deleted_by = user
    instance.save(update_fields=["is_active", "deleted_at", "deleted_by"])
    log_action(user, AuditLog.Action.DELETE, instance)


class SoftDeleteModelViewSet(viewsets.ModelViewSet):
    def perform_create(self, serializer):
        instance = serializer.save()
        log_action(self.request.user, AuditLog.Action.CREATE, instance)

    def perform_update(self, serializer):
        instance = serializer.save()
        log_action(self.request.user, AuditLog.Action.UPDATE, instance)

    def perform_destroy(self, instance):
        soft_delete_instance(instance, self.request.user)


class LoginView(APIView):
    authentication_classes = []  # no exigimos auth para loguear
    permission_classes = []      # cualquiera puede intentar loguearse

    def post(self, request, *args, **kwargs):
        serializer = LoginSerializer(data=request.data)
        if serializer.is_valid():
            user = serializer.validated_data["user"]

            # Por ahora devolvemos algo simple, sin JWT
            return Response(
                {
                    "id": user.id,
                    "email": user.email,
                    "first_name": user.first_name,
                    "last_name": user.last_name,
                    "role": user.role,
                },
                status=status.HTTP_200_OK,
            )

        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

class CustomTokenObtainPairView(TokenObtainPairView):
    serializer_class = CustomTokenObtainPairSerializer
    authentication_classes = []  # para pedir token no hace falta estar logueado
    permission_classes = []


class MeView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request, *args, **kwargs):
        serializer = ProfileSerializer(request.user)
        return Response(serializer.data)

    def patch(self, request, *args, **kwargs):
        serializer = ProfileSerializer(
            request.user, data=request.data, partial=True
        )
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(serializer.data)


class ChangePasswordView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request, *args, **kwargs):
        serializer = ChangePasswordSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = request.user
        user.set_password(serializer.validated_data["new_password"])
        user.save(update_fields=["password"])
        log_action(user, AuditLog.Action.PASSWORD_CHANGE, user)
        return Response({"detail": "Contraseña actualizada."})

class PacienteViewSet(SoftDeleteModelViewSet):
    """
    CRUD de pacientes.
    Requiere estar autenticado con JWT.
    """
    queryset = Paciente.objects.filter(is_active=True).order_by("-created_at")
    serializer_class = PacienteSerializer
    permission_classes = [permissions.IsAuthenticated]


class UserViewSet(SoftDeleteModelViewSet):
    """
    Gestión de usuarios (solo dueña).
    """
    queryset = User.objects.filter(is_active=True).order_by("email")
    serializer_class = UserSerializer
    permission_classes = [permissions.IsAuthenticated, IsDuena]


class ConsultorioViewSet(SoftDeleteModelViewSet):
    """
    CRUD de consultorios.
    """
    queryset = Consultorio.objects.filter(is_active=True).order_by("numero")
    serializer_class = ConsultorioSerializer
    permission_classes = [permissions.IsAuthenticated, IsDuenaOrReadOnly]


class TurnoViewSet(SoftDeleteModelViewSet):
    """
    Agenda de turnos. Profesionales ven sus turnos, dueña ve todos.
    """
    serializer_class = TurnoSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        user = self.request.user
        qs = Turno.objects.select_related(
            "paciente", "profesional", "consultorio"
        ).filter(is_active=True)
        if user.role != User.Role.DUENA:
            qs = qs.filter(profesional=user)

        params = self.request.query_params
        paciente_id = params.get("paciente")
        profesional_id = params.get("profesional")
        consultorio_id = params.get("consultorio")
        consultorio_numero = params.get("consultorio_numero")
        estado = params.get("estado")
        date_str = params.get("date")
        start_str = params.get("start")
        end_str = params.get("end")

        if paciente_id:
            qs = qs.filter(paciente_id=paciente_id)

        if consultorio_id:
            qs = qs.filter(consultorio_id=consultorio_id)
        elif consultorio_numero:
            qs = qs.filter(consultorio__numero=consultorio_numero)

        if estado:
            qs = qs.filter(estado=estado)

        if user.role == User.Role.DUENA and profesional_id:
            qs = qs.filter(profesional_id=profesional_id)

        if date_str:
            date_value = parse_date(date_str)
            if date_value:
                qs = qs.filter(inicio__date=date_value)

        start_dt = parse_datetime(start_str) if start_str else None
        end_dt = parse_datetime(end_str) if end_str else None

        if start_dt and end_dt:
            qs = qs.filter(inicio__lt=end_dt, fin__gt=start_dt)
        elif start_dt:
            qs = qs.filter(fin__gte=start_dt)
        elif end_dt:
            qs = qs.filter(inicio__lt=end_dt)

        return qs.order_by("inicio")

    def perform_create(self, serializer):
        user = self.request.user
        if user.role == User.Role.DUENA:
            profesional_id = self.request.data.get("profesional")
            if profesional_id:
                profesional = User.objects.filter(pk=profesional_id).first()
                if profesional:
                    instance = serializer.save(profesional=profesional)
                    log_action(user, AuditLog.Action.CREATE, instance)
                    return
            instance = serializer.save(profesional=user)
            log_action(user, AuditLog.Action.CREATE, instance)
            return
        instance = serializer.save(profesional=user)
        log_action(user, AuditLog.Action.CREATE, instance)


class EvolucionViewSet(SoftDeleteModelViewSet):
    """
    Evolución clínica por paciente.
    """
    serializer_class = EvolucionSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        qs = Evolucion.objects.select_related("paciente", "profesional").filter(
            is_active=True
        )
        params = self.request.query_params
        paciente_id = params.get("paciente")
        profesional_id = params.get("profesional")
        date_str = params.get("date")

        if paciente_id:
            qs = qs.filter(paciente_id=paciente_id)
        if profesional_id:
            qs = qs.filter(profesional_id=profesional_id)
        if date_str:
            date_value = parse_date(date_str)
            if date_value:
                qs = qs.filter(creado_en__date=date_value)

        return qs.order_by("-creado_en")

    def perform_create(self, serializer):
        instance = serializer.save(profesional=self.request.user)
        log_action(self.request.user, AuditLog.Action.CREATE, instance)

    def update(self, request, *args, **kwargs):
        return Response(
            {"detail": "Las evoluciones no se pueden editar."},
            status=status.HTTP_405_METHOD_NOT_ALLOWED,
        )

    def partial_update(self, request, *args, **kwargs):
        return Response(
            {"detail": "Las evoluciones no se pueden editar."},
            status=status.HTTP_405_METHOD_NOT_ALLOWED,
        )


class DocumentoViewSet(SoftDeleteModelViewSet):
    """
    Documentos adjuntos del paciente.
    """
    serializer_class = DocumentoSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        qs = Documento.objects.select_related("paciente").filter(is_active=True)
        params = self.request.query_params
        paciente_id = params.get("paciente")
        query = params.get("q")

        if paciente_id:
            qs = qs.filter(paciente_id=paciente_id)
        if query:
            qs = qs.filter(nombre__icontains=query)

        return qs.order_by("-creado_en")


class InformeViewSet(SoftDeleteModelViewSet):
    """
    Informes tipo Word del paciente.
    """
    serializer_class = InformeSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        qs = Informe.objects.select_related("paciente", "profesional").filter(
            is_active=True
        )
        params = self.request.query_params
        paciente_id = params.get("paciente")
        profesional_id = params.get("profesional")
        if paciente_id:
            qs = qs.filter(paciente_id=paciente_id)
        if profesional_id:
            qs = qs.filter(profesional_id=profesional_id)
        return qs.order_by("-actualizado_en")

    def perform_create(self, serializer):
        instance = serializer.save(profesional=self.request.user)
        log_action(self.request.user, AuditLog.Action.CREATE, instance)

    def _is_locked(self, informe):
        limite = timezone.now() - timezone.timedelta(days=30)
        return informe.creado_en < limite

    def update(self, request, *args, **kwargs):
        informe = self.get_object()
        if self._is_locked(informe):
            return Response(
                {"detail": "No se pueden modificar informes con más de un mes."},
                status=status.HTTP_403_FORBIDDEN,
            )
        return super().update(request, *args, **kwargs)

    def partial_update(self, request, *args, **kwargs):
        informe = self.get_object()
        if self._is_locked(informe):
            return Response(
                {"detail": "No se pueden modificar informes con más de un mes."},
                status=status.HTTP_403_FORBIDDEN,
            )
        return super().partial_update(request, *args, **kwargs)


class InvitacionViewSet(SoftDeleteModelViewSet):
    """
    Invitaciones para crear contraseña.
    """
    serializer_class = InvitacionSerializer
    permission_classes = [permissions.IsAuthenticated, IsDuena]

    def get_queryset(self):
        return Invitacion.objects.all().order_by("-creado_en")

    def perform_create(self, serializer):
        email = serializer.validated_data["email"].strip().lower()
        role = serializer.validated_data.get("role", User.Role.PROFESIONAL)
        token = get_random_string(48)
        expira_en = timezone.now() + timezone.timedelta(days=7)

        invitacion = serializer.save(
            email=email,
            role=role,
            token=token,
            expira_en=expira_en,
            creado_por=self.request.user,
        )
        log_action(self.request.user, AuditLog.Action.CREATE, invitacion)

        frontend_base = getattr(settings, "FRONTEND_BASE_URL", "http://localhost:5173")
        link = f"{frontend_base}/?invite={token}"
        send_mail(
            subject="Invitación a Lazos Digital",
            message=(
                "Fuiste invitado/a a Lazos Digital.\n\n"
                f"Creá tu contraseña aquí: {link}\n\n"
                "El enlace expira en 7 días."
            ),
            from_email=getattr(settings, "DEFAULT_FROM_EMAIL", None),
            recipient_list=[email],
            fail_silently=True,
        )
        return invitacion


class InvitacionAcceptView(APIView):
    authentication_classes = []
    permission_classes = []

    def post(self, request, *args, **kwargs):
        token = (request.data.get("token") or "").strip()
        password = request.data.get("password") or ""

        if not token or not password:
            return Response(
                {"detail": "Token y contraseña son obligatorios."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        invitacion = Invitacion.objects.filter(token=token).first()
        if not invitacion:
            return Response(
                {"detail": "Invitación inválida."},
                status=status.HTTP_404_NOT_FOUND,
            )

        if invitacion.usado_en:
            return Response(
                {"detail": "Esta invitación ya fue usada."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        if timezone.now() > invitacion.expira_en:
            return Response(
                {"detail": "La invitación expiró."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        user, _created = User.objects.get_or_create(
            email=invitacion.email,
            defaults={"role": invitacion.role, "is_enabled": True},
        )
        user.set_password(password)
        user.is_enabled = True
        user.save(update_fields=["password", "is_enabled"])

        invitacion.usado_en = timezone.now()
        invitacion.save(update_fields=["usado_en"])
        log_action(user, AuditLog.Action.INVITE_ACCEPT, invitacion)

        return Response({"detail": "Contraseña creada correctamente."})


class AuditLogViewSet(viewsets.ReadOnlyModelViewSet):
    serializer_class = AuditLogSerializer
    permission_classes = [permissions.IsAuthenticated, IsDuena]

    def get_queryset(self):
        return AuditLog.objects.select_related("actor").order_by("-created_at")

