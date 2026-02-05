from rest_framework import permissions


class IsDuena(permissions.BasePermission):
    def has_permission(self, request, view):
        user = request.user
        return bool(user and user.is_authenticated and user.role == "DUENA")


class IsDuenaOrReadOnly(permissions.BasePermission):
    def has_permission(self, request, view):
        if request.method in permissions.SAFE_METHODS:
            return bool(request.user and request.user.is_authenticated)
        return bool(
            request.user
            and request.user.is_authenticated
            and request.user.role == "DUENA"
        )


class IsOwnerOrDuena(permissions.BasePermission):
    def has_object_permission(self, request, view, obj):
        if request.user and request.user.is_authenticated and request.user.role == "DUENA":
            return True
        owner = getattr(obj, "profesional", None)
        return bool(owner and owner == request.user)
