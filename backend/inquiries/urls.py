from rest_framework.routers import DefaultRouter

from .views import AdminInquiryViewSet, ParentInquiryViewSet

router = DefaultRouter()
router.register("parent/inquiries", ParentInquiryViewSet, basename="parent-inquiries")
router.register("admin/inquiries", AdminInquiryViewSet, basename="admin-inquiries")

urlpatterns = router.urls
