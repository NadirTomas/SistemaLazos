"""lazos_backend URL Configuration"""
from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
from rest_framework.routers import DefaultRouter
from core.views import (
    LoginView,
    CustomTokenObtainPairView,
    PacienteViewSet,
    UserViewSet,
    ConsultorioViewSet,
    TurnoViewSet,
    EvolucionViewSet,
    DocumentoViewSet,
    InformeViewSet,
    InvitacionViewSet,
    InvitacionAcceptView,
    MeView,
    ChangePasswordView,
    AuditLogViewSet,
)

router = DefaultRouter()
router.register(r'usuarios', UserViewSet, basename='usuario')
router.register(r'pacientes', PacienteViewSet, basename='paciente')
router.register(r'consultorios', ConsultorioViewSet, basename='consultorio')
router.register(r'turnos', TurnoViewSet, basename='turno')
router.register(r'evoluciones', EvolucionViewSet, basename='evolucion')
router.register(r'documentos', DocumentoViewSet, basename='documento')
router.register(r'informes', InformeViewSet, basename='informe')
router.register(r'invitaciones', InvitacionViewSet, basename='invitacion')
router.register(r'audit-logs', AuditLogViewSet, basename='audit_log')

urlpatterns = [
    path("admin/", admin.site.urls),
    path("api/auth/login/", LoginView.as_view(), name="login"),
    path("api/auth/token/", CustomTokenObtainPairView.as_view(), name="token_obtain_pair"),
    path("api/auth/me/", MeView.as_view(), name="auth_me"),
    path("api/auth/change-password/", ChangePasswordView.as_view(), name="auth_change_password"),
    path("api/invitaciones/accept/", InvitacionAcceptView.as_view(), name="invitacion_accept"),
    path('api/', include(router.urls)),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
