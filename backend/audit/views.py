from rest_framework import viewsets

from accounts.permissions import IsAdminRole

from .models import AuditLog
from .serializers import AuditLogSerializer


class AuditLogViewSet(viewsets.ReadOnlyModelViewSet):
    permission_classes = [IsAdminRole]
    serializer_class = AuditLogSerializer
    queryset = AuditLog.objects.select_related("actor")
    filterset_fields = ["action", "entity_type", "actor"]
    search_fields = ["action", "detail", "actor__full_name"]
    ordering_fields = ["created_at"]
