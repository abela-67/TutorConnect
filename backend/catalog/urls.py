from django.urls import path
from rest_framework.routers import DefaultRouter

from .views import AdminGradeLevelViewSet, AdminLocationViewSet, AdminSubjectViewSet, ReferenceDataView

router = DefaultRouter()
router.register("admin/subjects", AdminSubjectViewSet, basename="admin-subjects")
router.register("admin/grade-levels", AdminGradeLevelViewSet, basename="admin-grade-levels")
router.register("admin/locations", AdminLocationViewSet, basename="admin-locations")

urlpatterns = [path("reference/", ReferenceDataView.as_view(), name="reference-data")] + router.urls
