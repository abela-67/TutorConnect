from rest_framework.routers import DefaultRouter

from .views import AuditLogViewSet

router = DefaultRouter()
router.register("admin/audit-logs", AuditLogViewSet, basename="admin-audit-logs")

urlpatterns = router.urls
