from django.urls import path
from rest_framework.routers import DefaultRouter

from .views import (
    AdminDocumentViewSet,
    AdminQualificationViewSet,
    AdminTutorViewSet,
    DocumentDownloadView,
    MyAvailabilityViewSet,
    MyDocumentViewSet,
    MyPhotoView,
    MyProfileView,
    MyQualificationViewSet,
    PublicTutorViewSet,
    SubmitApplicationView,
)

router = DefaultRouter()
router.register("tutors", PublicTutorViewSet, basename="tutors")
router.register("tutor/qualifications", MyQualificationViewSet, basename="my-qualifications")
router.register("tutor/documents", MyDocumentViewSet, basename="my-documents")
router.register("tutor/availability", MyAvailabilityViewSet, basename="my-availability")
router.register("admin/tutors", AdminTutorViewSet, basename="admin-tutors")
router.register("admin/documents", AdminDocumentViewSet, basename="admin-documents")
router.register("admin/qualifications", AdminQualificationViewSet, basename="admin-qualifications")

urlpatterns = [
    path("tutor/profile/", MyProfileView.as_view(), name="my-profile"),
    path("tutor/profile/photo/", MyPhotoView.as_view(), name="my-photo"),
    path("tutor/profile/submit/", SubmitApplicationView.as_view(), name="my-submit"),
    path("documents/<int:pk>/download/", DocumentDownloadView.as_view(), name="document-download"),
] + router.urls
