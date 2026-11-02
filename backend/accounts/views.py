from rest_framework import generics, status, viewsets
from rest_framework.decorators import action
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.throttling import ScopedRateThrottle
from rest_framework_simplejwt.views import TokenObtainPairView

from audit.services import log
from notifications.services import notify_admins

from .models import User
from .permissions import IsAdminRole
from .serializers import (
    AccountUpdateSerializer,
    AdminUserSerializer,
    ChangePasswordSerializer,
    EmailTokenObtainPairSerializer,
    ParentRegisterSerializer,
    TutorRegisterSerializer,
    UserSerializer,
)


class LoginView(TokenObtainPairView):
    serializer_class = EmailTokenObtainPairSerializer
    throttle_classes = [ScopedRateThrottle]
    throttle_scope = "auth"


class _RegisterView(generics.CreateAPIView):
    permission_classes = [AllowAny]
    authentication_classes = []
    throttle_classes = [ScopedRateThrottle]
    throttle_scope = "auth"

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = serializer.save()
        return Response(UserSerializer(user).data, status=status.HTTP_201_CREATED)


class ParentRegisterView(_RegisterView):
    serializer_class = ParentRegisterSerializer


class TutorRegisterView(_RegisterView):
    serializer_class = TutorRegisterSerializer

    def create(self, request, *args, **kwargs):
        response = super().create(request, *args, **kwargs)
        notify_admins("New tutor registration", "A tutor has registered and is completing their profile.", "/admin/tutors", "tutor")
        return response


class MeView(generics.RetrieveUpdateAPIView):
    """Signed-in user's own account. Role and email cannot be changed here."""

    def get_serializer_class(self):
        return AccountUpdateSerializer if self.request.method in ("PUT", "PATCH") else UserSerializer

    def get_object(self):
        return self.request.user

    def update(self, request, *args, **kwargs):
        serializer = AccountUpdateSerializer(self.get_object(), data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(UserSerializer(self.get_object()).data)


class ChangePasswordView(generics.GenericAPIView):
    serializer_class = ChangePasswordSerializer

    def post(self, request):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        request.user.set_password(serializer.validated_data["new_password"])
        request.user.save(update_fields=["password"])
        return Response({"detail": "Password updated."})


class AdminUserViewSet(viewsets.ReadOnlyModelViewSet):
    """Parent and tutor account management. Administrator accounts cannot be changed through the API."""

    permission_classes = [IsAdminRole]
    serializer_class = AdminUserSerializer
    queryset = User.objects.all()
    filterset_fields = ["role", "is_active"]
    search_fields = ["email", "full_name", "phone"]
    ordering_fields = ["created_at", "full_name"]

    def _toggle(self, request, active):
        user = self.get_object()
        if user.role == User.Role.ADMIN:
            return Response({"detail": "Administrator accounts cannot be changed here."}, status=status.HTTP_403_FORBIDDEN)
        user.is_active = active
        user.save(update_fields=["is_active"])
        log(request.user, "user_reactivated" if active else "user_suspended", user, f"role={user.role}")
        return Response(AdminUserSerializer(user).data)

    @action(detail=True, methods=["post"])
    def suspend(self, request, pk=None):
        return self._toggle(request, False)

    @action(detail=True, methods=["post"])
    def reactivate(self, request, pk=None):
        return self._toggle(request, True)
