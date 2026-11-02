from decimal import Decimal

from rest_framework import mixins, status, viewsets
from rest_framework.decorators import action
from rest_framework.exceptions import ValidationError
from rest_framework.response import Response
from rest_framework.throttling import ScopedRateThrottle

import django_filters as df

from accounts.permissions import IsAdminRole, IsParent
from audit.services import log, record_status
from notifications.services import notify, notify_admins
from tutors.matching import find_candidates
from tutors.serializers import TutorListSerializer

from . import services
from .models import ParentRequest
from .serializers import (
    AdminRequestSerializer,
    AssignSerializer,
    ParentRequestCreateSerializer,
    ParentRequestSerializer,
    SetStatusSerializer,
)


class ParentRequestViewSet(mixins.CreateModelMixin, mixins.ListModelMixin, mixins.RetrieveModelMixin, viewsets.GenericViewSet):
    """A parent can only ever see and act on their own requests."""

    permission_classes = [IsParent]
    filterset_fields = ["status"]
    ordering = ["-created_at"]

    def get_throttles(self):
        if self.action == "create":
            self.throttle_scope = "submit"
            return [ScopedRateThrottle()]
        return super().get_throttles()

    def get_queryset(self):
        # Drafts are administrator work-in-progress and are never shown to parents.
        return ParentRequest.objects.filter(parent=self.request.user).exclude(status=ParentRequest.Status.DRAFT).select_related(
            "subject", "grade_level", "location", "preferred_tutor"
        )

    def get_serializer_class(self):
        return ParentRequestCreateSerializer if self.action == "create" else ParentRequestSerializer

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        req = serializer.save()
        record_status(req, "", req.status, request.user, "Submitted online")
        notify(request.user, "Request received", f"We received your request {req.reference}.", "/parent/requests", "request")
        notify_admins("New parent request", f"{req.reference} was submitted online.", f"/admin/requests/{req.id}", "request")
        return Response(ParentRequestSerializer(req).data, status=status.HTTP_201_CREATED)

    @action(detail=True, methods=["post"])
    def cancel(self, request, pk=None):
        req = self.get_object()
        if not req.is_open:
            raise ValidationError({"detail": "This request is already closed."})
        services.change_status(req, ParentRequest.Status.CANCELLED, request.user, latest_update="Cancelled by parent", note="Cancelled by parent")
        notify_admins("Parent cancelled a request", f"{req.reference} was cancelled by the parent.", f"/admin/requests/{req.id}", "request")
        return Response(ParentRequestSerializer(req).data)


class AdminRequestFilter(df.FilterSet):
    open = df.BooleanFilter(method="filter_open")
    mine = df.BooleanFilter(method="filter_mine")
    unassigned = df.BooleanFilter(method="filter_unassigned")

    class Meta:
        model = ParentRequest
        fields = ["status", "source", "assigned_to", "subject", "grade_level", "location"]

    def filter_open(self, qs, name, value):
        closed = ParentRequest.CLOSED_STATUSES
        return qs.exclude(status__in=closed) if value else qs.filter(status__in=closed)

    def filter_mine(self, qs, name, value):
        return qs.filter(assigned_to=self.request.user) if value else qs

    def filter_unassigned(self, qs, name, value):
        return qs.filter(assigned_to__isnull=True) if value else qs.filter(assigned_to__isnull=False)


class AdminRequestViewSet(viewsets.ModelViewSet):
    """Administrators can view, record (e.g. telephone) and process every request. Requests are never deleted."""

    permission_classes = [IsAdminRole]
    serializer_class = AdminRequestSerializer
    filterset_class = AdminRequestFilter
    search_fields = ["contact_name", "contact_phone", "contact_email", "parent__full_name", "parent__email", "subject__name"]
    ordering_fields = ["created_at", "updated_at", "status"]
    http_method_names = ["get", "post", "patch", "head", "options"]

    def get_queryset(self):
        return ParentRequest.objects.select_related(
            "parent", "subject", "grade_level", "location", "preferred_tutor", "assigned_to"
        ).prefetch_related("jobs__applications")

    def perform_create(self, serializer):
        req = serializer.save()
        record_status(req, "", req.status, self.request.user, f"Recorded by administrator ({req.get_source_display()})")
        log(self.request.user, "request_recorded", req, f"source={req.source}")

    def perform_update(self, serializer):
        req = serializer.save()
        log(self.request.user, "request_updated", req)

    @action(detail=True, methods=["post"], url_path="set-status")
    def set_status(self, request, pk=None):
        serializer = SetStatusSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        d = serializer.validated_data
        req = services.change_status(
            self.get_object(), d["status"], request.user,
            latest_update=d.get("latest_update"), outcome=d.get("outcome"), note=d.get("note", ""),
        )
        return Response(self.get_serializer(req).data)

    @action(detail=True, methods=["post"])
    def assign(self, request, pk=None):
        serializer = AssignSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        req = self.get_object()
        req.assigned_to = serializer.validated_data["admin"]
        req.save(update_fields=["assigned_to", "updated_at"])
        log(request.user, "request_assigned", req, f"to={req.assigned_to_id}")
        if req.assigned_to_id and req.assigned_to_id != request.user.id:
            notify(req.assigned_to, "A request was assigned to you", req.reference, f"/admin/requests/{req.id}", "request")
        return Response(self.get_serializer(req).data)

    @action(detail=True, methods=["get"])
    def matches(self, request, pk=None):
        """Suggested approved tutors for this request (suggestions only; the administrator decides)."""
        req = self.get_object()
        gender = req.preferred_gender if req.preferred_gender in ("male", "female") else ""
        results = find_candidates(
            subject=req.subject,
            grade_level=req.grade_level,
            location=req.location,
            mode=req.teaching_mode,
            gender=gender,
            budget=Decimal(req.budget_amount) if req.budget_amount is not None else None,
        )
        payload = []
        for r in results:
            item = TutorListSerializer(r["tutor"], context={"request": request}).data
            item.update({"score": r["score"], "reasons": r["reasons"], "concerns": r["concerns"], "verified_documents": r["tutor"].verified_docs})
            payload.append(item)
        return Response({"request": req.id, "preferred_tutor": req.preferred_tutor_id, "results": payload})

    @action(detail=True, methods=["post"], url_path="create-job")
    def create_job(self, request, pk=None):
        """Create a DRAFT job pre-filled from this request. Private details and free text are never copied."""
        from jobs.serializers import AdminJobSerializer
        from jobs.services import create_job_from_request

        req = self.get_object()
        job = create_job_from_request(req, request.user)
        return Response(AdminJobSerializer(job, context={"request": request}).data, status=status.HTTP_201_CREATED)
