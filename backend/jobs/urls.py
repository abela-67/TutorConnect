from rest_framework.routers import DefaultRouter

from .views import AdminApplicationViewSet, AdminJobViewSet, TutorApplicationViewSet, TutorJobViewSet

router = DefaultRouter()
router.register("tutor/jobs", TutorJobViewSet, basename="tutor-jobs")
router.register("tutor/applications", TutorApplicationViewSet, basename="tutor-applications")
router.register("admin/jobs", AdminJobViewSet, basename="admin-jobs")
router.register("admin/applications", AdminApplicationViewSet, basename="admin-applications")

urlpatterns = router.urls
