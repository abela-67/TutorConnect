from rest_framework.routers import DefaultRouter

from .views import AdminRequestViewSet, ParentRequestViewSet

router = DefaultRouter()
router.register("parent/requests", ParentRequestViewSet, basename="parent-requests")
router.register("admin/requests", AdminRequestViewSet, basename="admin-requests")

urlpatterns = router.urls
