import django_filters as df
from django.db import IntegrityError, transaction
from django.db.models import Prefetch, Q
from django.utils import timezone
from rest_framework import mixins, status, viewsets
from rest_framework.decorators import action
from rest_framework.exceptions import ValidationError
from rest_framework.response import Response

from accounts.permissions import IsAdminRole, IsApprovedTutor, IsTutor
from audit.services import log, record_status
from notifications.services import notify_admins

from . import services
from .models import JobApplication, TutoringJob
from .serializers import (
    AdminApplicationSerializer,
    AdminJobSerializer,
    ApplyJobSerializer,
    FinalizeSerializer,
    SetApplicationStatusSerializer,
    SetJobStatusSerializer,
    TutorApplicationSerializer,
    TutorJobSerializer,
)

A = JobApplication.Status


# ---------------------------------------------------------------- tutor job board

class TutorJobFilter(df.FilterSet):
    subject = df.NumberFilter(field_name="subject_id")
    location = df.NumberFilter(field_name="location_id")
    city = df.CharFilter(field_name="location__city", lookup_expr="iexact")
    grade_level = df.NumberFilter(field_name="grade_level_id")
    teaching_mode = df.ChoiceFilter(choices=[("online", "Online"), ("in_person", "In person")], method="filter_mode")
    min_pay = df.NumberFilter(field_name="payment_amount", lookup_expr="gte")
    max_pay = df.NumberFilter(field_name="payment_amount", lookup_expr="lte")
    q = df.CharFilter(method="filter_q")

    class Meta:
        model = TutoringJob
        fields = []

    def filter_mode(self, qs, name, value):
        return qs.filter(teaching_mode__in=[value, "either"])

    def filter_q(self, qs, name, value):
        value = value.strip()
        if not value:
            return qs
        return qs.filter(Q(title__icontains=value) | Q(preferred_schedule__icontains=value) | Q(frequency__icontains=value))


class TutorJobViewSet(mixins.ListModelMixin, mixins.RetrieveModelMixin, viewsets.GenericViewSet):
    """Private job board: approved, active tutors only. Lists open jobs; detail also works for jobs the tutor applied to."""

    permission_classes = [IsApprovedTutor]
    serializer_class = TutorJobSerializer
    filterset_class = TutorJobFilter
    ordering_fields = ["published_at", "payment_amount", "application_deadline"]
    ordering = ["-published_at"]

    def _base(self):
        mine = Prefetch("applications", queryset=JobApplication.objects.filter(tutor=self.request.user.tutor_profile))
        return TutoringJob.objects.select_related("subject", "grade_level", "location").prefetch_related(mine)

    def get_queryset(self):
        qs = self._base()
        today = timezone.localdate()
        if self.action == "list":
            return qs.filter(status__in=TutoringJob.ACCEPTING).filter(Q(application_deadline__isnull=True) | Q(application_deadline__gte=today))
        return qs.exclude(status=TutoringJob.Status.DRAFT).filter(
            Q(status__in=TutoringJob.ACCEPTING) | Q(applications__tutor=self.request.user.tutor_profile)
        ).distinct()

    @action(detail=True, methods=["post"])
    def apply(self, request, pk=None):
        job = self.get_object()
        serializer = ApplyJobSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        tutor = request.user.tutor_profile
        message = serializer.validated_data.get("message", "")

        if not services.is_accepting(job):
            raise ValidationError({"detail": "This job is no longer accepting applications."})

        try:
            with transaction.atomic():
                existing = JobApplication.objects.select_for_update().filter(job=job, tutor=tutor).first()
                if existing:
                    if existing.status != A.WITHDRAWN:
                        raise ValidationError({"detail": "You have already applied for this job."})
                    # deliberate resubmission after withdrawing
                    old = existing.status
                    existing.status, existing.message = A.SUBMITTED, message
                    existing.save()
                    record_status(existing, old, A.SUBMITTED, request.user, "Resubmitted")
                    app = existing
                else:
                    app = JobApplication.objects.create(job=job, tutor=tutor, message=message)
                    record_status(app, "", A.SUBMITTED, request.user, "Applied")
        except IntegrityError:
            raise ValidationError({"detail": "You have already applied for this job."})

        notify_admins("New job application", f"{tutor.display_name} applied for {job.reference}.", f"/admin/jobs/{job.id}", "job")
        return Response(TutorApplicationSerializer(app, context={"request": request}).data, status=status.HTTP_201_CREATED)


class TutorApplicationViewSet(mixins.ListModelMixin, mixins.RetrieveModelMixin, viewsets.GenericViewSet):
    """A tutor sees only their own applications."""

    permission_classes = [IsTutor]
    serializer_class = TutorApplicationSerializer
    filterset_fields = ["status"]
    ordering = ["-created_at"]

    def get_queryset(self):
        tutor = self.request.user.tutor_profile
        mine = Prefetch("job__applications", queryset=JobApplication.objects.filter(tutor=tutor))
        return (
            JobApplication.objects.filter(tutor=tutor)
            .select_related("job", "job__subject", "job__grade_level", "job__location")
            .prefetch_related(mine)
        )

    @action(detail=True, methods=["post"])
    def withdraw(self, request, pk=None):
        app = self.get_object()
        if app.status not in JobApplication.ACTIVE:
            raise ValidationError({"detail": "This application can no longer be withdrawn. Contact the administrator."})
        old = app.status
        app.status = A.WITHDRAWN
        app.save()
        record_status(app, old, A.WITHDRAWN, request.user, "Withdrawn by tutor")
        notify_admins("Application withdrawn", f"A tutor withdrew from {app.job.reference}.", f"/admin/jobs/{app.job_id}", "job")
        return Response(self.get_serializer(app).data)


# ---------------------------------------------------------------- administrator

class AdminJobFilter(df.FilterSet):
    class Meta:
        model = TutoringJob
        fields = ["status", "subject", "grade_level", "location", "source_request", "teaching_mode"]


class AdminJobViewSet(viewsets.ModelViewSet):
    permission_classes = [IsAdminRole]
    serializer_class = AdminJobSerializer
    filterset_class = AdminJobFilter
    search_fields = ["title", "subject__name"]
    ordering_fields = ["created_at", "published_at", "application_deadline", "status"]
    http_method_names = ["get", "post", "patch", "head", "options"]

    def get_queryset(self):
        return TutoringJob.objects.select_related("subject", "grade_level", "location", "source_request").prefetch_related("applications")

    def perform_create(self, serializer):
        job = serializer.save(created_by=self.request.user, status=TutoringJob.Status.DRAFT)
        record_status(job, "", job.status, self.request.user, "Created")
        log(self.request.user, "job_created", job)

    def perform_update(self, serializer):
        job = serializer.save()
        log(self.request.user, "job_updated", job)

    @action(detail=True, methods=["post"])
    def publish(self, request, pk=None):
        job = self.get_object()
        if job.status != TutoringJob.Status.DRAFT:
            raise ValidationError({"detail": "Only draft jobs can be published. Use 'reopen' for closed jobs."})
        services.change_job_status(job, TutoringJob.Status.OPEN, request.user, "Published")
        return Response(self.get_serializer(job).data)

    @action(detail=True, methods=["post"], url_path="set-status")
    def set_status(self, request, pk=None):
        serializer = SetJobStatusSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        job = self.get_object()
        if job.status == TutoringJob.Status.DRAFT and serializer.validated_data["status"] != TutoringJob.Status.OPEN:
            if serializer.validated_data["status"] != TutoringJob.Status.CANCELLED:
                raise ValidationError({"detail": "Publish the draft first."})
        services.change_job_status(job, serializer.validated_data["status"], request.user, serializer.validated_data.get("note", ""))
        return Response(self.get_serializer(job).data)

    @action(detail=True, methods=["post"])
    def finalize(self, request, pk=None):
        serializer = FinalizeSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        job = services.finalize_job(self.get_object(), request.user, serializer.validated_data.get("outcome", ""))
        return Response(self.get_serializer(job).data)

    @action(detail=True, methods=["get"])
    def applications(self, request, pk=None):
        job = self.get_object()
        qs = (
            job.applications.select_related("job", "tutor", "tutor__location", "tutor__user")
            .prefetch_related("tutor__subjects", "tutor__grade_levels", "tutor__qualifications", "tutor__documents")
        )
        return Response(AdminApplicationSerializer(qs, many=True, context={"request": request}).data)


class AdminApplicationViewSet(mixins.ListModelMixin, mixins.RetrieveModelMixin, viewsets.GenericViewSet):
    permission_classes = [IsAdminRole]
    serializer_class = AdminApplicationSerializer
    filterset_fields = ["job", "status", "tutor"]
    search_fields = ["tutor__display_name", "job__title"]
    ordering = ["-created_at"]

    def get_queryset(self):
        return (
            JobApplication.objects.select_related("job", "tutor", "tutor__location", "tutor__user")
            .prefetch_related("tutor__subjects", "tutor__grade_levels", "tutor__qualifications", "tutor__documents")
        )

    @action(detail=True, methods=["post"], url_path="set-status")
    def set_status(self, request, pk=None):
        serializer = SetApplicationStatusSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        app = self.get_object()
        d = serializer.validated_data
        if "admin_notes" in d:
            app.admin_notes = d["admin_notes"]
            app.save(update_fields=["admin_notes", "updated_at"])
        services.change_application_status(app, d["status"], request.user, d.get("note", ""))
        return Response(self.get_serializer(app).data)
