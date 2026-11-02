from rest_framework.routers import DefaultRouter

from .views import AdminIntroductionViewSet, ParentIntroductionViewSet

router = DefaultRouter()
router.register("parent/introductions", ParentIntroductionViewSet, basename="parent-introductions")
router.register("admin/introductions", AdminIntroductionViewSet, basename="admin-introductions")

urlpatterns = router.urls
