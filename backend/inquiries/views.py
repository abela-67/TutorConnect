from rest_framework import mixins, status, viewsets
from rest_framework.decorators import action
from rest_framework.exceptions import ValidationError
from rest_framework.response import Response
from rest_framework.throttling import ScopedRateThrottle

from accounts.permissions import IsAdminRole, IsParent
from audit.services import log, record_status
from notifications.services import notify, notify_admins
from tutor_requests.models import ParentRequest

from .models import PersonalInquiry
from .serializers import (
    AdminInquirySerializer,
    InquiryCreateSerializer,
    InquiryStatusSerializer,
    ParentInquirySerializer,
    RespondSerializer,
)

S = PersonalInquiry.Status


class ParentInquiryViewSet(mixins.CreateModelMixin, mixins.ListModelMixin, mixins.RetrieveModelMixin, viewsets.GenericViewSet):
    """Parents see only their own inquiries."""

    permission_classes = [IsParent]
    ordering = ["-created_at"]

    def get_throttles(self):
        if self.action == "create":
            self.throttle_scope = "submit"
            return [ScopedRateThrottle()]
        return super().get_throttles()

    def get_queryset(self):
        return PersonalInquiry.objects.filter(parent=self.request.user).select_related("about_tutor")

    def get_serializer_class(self):
        return InquiryCreateSerializer if self.action == "create" else ParentInquirySerializer

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        inquiry = serializer.save()
        record_status(inquiry, "", inquiry.status, request.user, "Submitted")
        notify(request.user, "Message received", f"We received your message {inquiry.reference}.", "/parent/contact", "inquiry")
        notify_admins("New parent inquiry", f"{inquiry.reference}: {inquiry.get_category_display()}", f"/admin/inquiries/{inquiry.id}", "inquiry")
        return Response(ParentInquirySerializer(inquiry).data, status=status.HTTP_201_CREATED)


class AdminInquiryViewSet(mixins.ListModelMixin, mixins.RetrieveModelMixin, mixins.UpdateModelMixin, viewsets.GenericViewSet):
    permission_classes = [IsAdminRole]
    serializer_class = AdminInquirySerializer
    filterset_fields = ["status", "category", "assigned_to", "parent"]
    search_fields = ["message", "parent__full_name", "parent__email"]
    ordering_fields = ["created_at", "status"]
    http_method_names = ["get", "patch", "post", "head", "options"]

    def get_queryset(self):
        return PersonalInquiry.objects.select_related("parent", "about_tutor", "assigned_to", "converted_request")

    def perform_update(self, serializer):
        inquiry = serializer.save()
        log(self.request.user, "inquiry_updated", inquiry)

    def _set(self, inquiry, new_status, actor, note=""):
        old = inquiry.status
        inquiry.status = new_status
        inquiry.save()
        if old != new_status:
            record_status(inquiry, old, new_status, actor, note)
            log(actor, "inquiry_status_changed", inquiry, f"{old} -> {new_status}")

    @action(detail=True, methods=["post"], url_path="set-status")
    def set_status(self, request, pk=None):
        serializer = InquiryStatusSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        inquiry = self.get_object()
        self._set(inquiry, serializer.validated_data["status"], request.user, serializer.validated_data.get("note", ""))
        return Response(self.get_serializer(inquiry).data)

    @action(detail=True, methods=["post"])
    def respond(self, request, pk=None):
        serializer = RespondSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        inquiry = self.get_object()
        inquiry.admin_response = serializer.validated_data["response"]
        self._set(inquiry, serializer.validated_data.get("status", S.AWAITING_PARENT), request.user, "Responded")
        notify(inquiry.parent, "We replied to your message", f"Open Contact Administrator to read the reply ({inquiry.reference}).", "/parent/contact", "inquiry")
        return Response(self.get_serializer(inquiry).data)

    @action(detail=True, methods=["post"], url_path="convert-to-request")
    def convert_to_request(self, request, pk=None):
        """Create a (draft) parent request for the same parent so it can be processed like any other request."""
        inquiry = self.get_object()
        if inquiry.converted_request_id:
            raise ValidationError({"detail": "This inquiry was already converted."})
        req = ParentRequest.objects.create(
            parent=inquiry.parent,
            source=ParentRequest.Source.INQUIRY,
            status=ParentRequest.Status.DRAFT,
            preferred_tutor=inquiry.about_tutor if inquiry.about_tutor and inquiry.about_tutor.is_publicly_listed else None,
            internal_notes=f"Converted from {inquiry.reference}.",
            assigned_to=request.user,
        )
        record_status(req, "", req.status, request.user, f"Converted from {inquiry.reference}")
        inquiry.converted_request = req
        inquiry.save(update_fields=["converted_request", "updated_at"])
        if inquiry.status == S.NEW:
            self._set(inquiry, S.IN_PROGRESS, request.user, "Converted to request")
        log(request.user, "inquiry_converted", inquiry, f"request={req.pk}")
        return Response({"request": req.id, "reference": req.reference}, status=status.HTTP_201_CREATED)
