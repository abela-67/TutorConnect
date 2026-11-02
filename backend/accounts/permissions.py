from rest_framework.permissions import BasePermission


class _RolePermission(BasePermission):
    role = None
    message = "You do not have permission to perform this action."

    def has_permission(self, request, view):
        user = request.user
        return bool(user and user.is_authenticated and user.is_active and user.role == self.role)


class IsParent(_RolePermission):
    role = "parent"


class IsTutor(_RolePermission):
    role = "tutor"


class IsAdminRole(_RolePermission):
    role = "admin"


class IsApprovedTutor(BasePermission):
    """Tutor whose profile is approved and whose account is active. Required for the job board."""

    message = "Your tutor profile must be approved before you can use the job board."

    def has_permission(self, request, view):
        user = request.user
        if not (user and user.is_authenticated and user.is_active and user.role == "tutor"):
            return False
        profile = getattr(user, "tutor_profile", None)
        return bool(profile and profile.status == "approved")
