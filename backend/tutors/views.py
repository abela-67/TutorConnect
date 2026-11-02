import mimetypes

from django.http import FileResponse, Http404
from rest_framework import mixins, status, viewsets
from rest_framework.decorators import action
from rest_framework.generics import RetrieveUpdateAPIView
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView
from django.utils import timezone

from accounts.permissions import IsAdminRole, IsTutor
from audit.services import log, record_status
from notifications.services import notify

from . import services
from .filters import TutorFilter
from .models import TutorAvailability, TutorDocument, TutorProfile, TutorQualification
from .serializers import (
    AdminDocumentSerializer,
    AdminQualificationSerializer,
    AdminTutorDetailSerializer,
    AdminTutorListSerializer,
    AvailabilitySerializer,
    DocumentReviewSerializer,
    DocumentSerializer,
    PhotoSerializer,
    QualificationSerializer,
    ReviewNoteSerializer,
    TutorDetailSerializer,
    TutorListSerializer,
    TutorProfileSelfSerializer,
)


# ---------------------------------------------------------------- public directory

def _public_queryset():
    return (
        TutorProfile.objects.public()
        .select_related("location")
        .prefetch_related("subjects", "grade_levels", "qualifications", "availability")
    )


class PublicTutorViewSet(viewsets.ReadOnlyModelViewSet):
    """Approved, active tutors only. No authentication required."""

    permission_classes = [AllowAny]
    authentication_classes = []
    filterset_class = TutorFilter
    ordering_fields = ["years_experience", "rate_amount", "created_at"]
    ordering = ["-years_experience", "display_name"]

    def get_queryset(self):
        return _public_queryset()

    def get_serializer_class(self):
        return TutorDetailSerializer if self.action == "retrieve" else TutorListSerializer

    @action(detail=False, methods=["get"])
    def featured(self, request):
        qs = self.get_queryset().order_by("-years_experience", "-updated_at")[:6]
        return Response(TutorListSerializer(qs, many=True, context={"request": request}).data)


# ---------------------------------------------------------------- tutor self-service

class TutorOwnedMixin:
    permission_classes = [IsTutor]

    def profile(self):
        return self.request.user.tutor_profile


class MyProfileView(RetrieveUpdateAPIView):
    permission_classes = [IsTutor]
    serializer_class = TutorProfileSelfSerializer
    http_method_names = ["get", "patch", "head", "options"]

    def get_object(self):
        return self.request.user.tutor_profile

    def perform_update(self, serializer):
        profile = self.get_object()
        services.ensure_editable(profile)
        sensitive_changed = any(k in serializer.validated_data for k in ("subjects", "grade_levels", "years_experience"))
        serializer.save()
        # display name of an approved tutor is public; keep tutor-supplied claims flagged for review
        if sensitive_changed:
            services.mark_changed_after_approval(profile, "subjects, grades or experience")
        services.refresh_draft_state(profile)


class MyPhotoView(APIView):
    permission_classes = [IsTutor]

    def post(self, request):
        profile = request.user.tutor_profile
        services.ensure_editable(profile)
        serializer = PhotoSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        profile.photo = serializer.validated_data["photo"]
        profile.save(update_fields=["photo", "updated_at"])
        return Response(TutorProfileSelfSerializer(profile, context={"request": request}).data)

    def delete(self, request):
        profile = request.user.tutor_profile
        services.ensure_editable(profile)
        profile.photo.delete(save=False)
        profile.photo = ""
        profile.save(update_fields=["photo", "updated_at"])
        return Response(status=status.HTTP_204_NO_CONTENT)


class SubmitApplicationView(APIView):
    permission_classes = [IsTutor]

    def post(self, request):
        profile = services.apply_action(request.user.tutor_profile, "submit", request.user)
        return Response(TutorProfileSelfSerializer(profile, context={"request": request}).data)


class MyQualificationViewSet(TutorOwnedMixin, viewsets.ModelViewSet):
    serializer_class = QualificationSerializer
    pagination_class = None

    def get_queryset(self):
        return TutorQualification.objects.filter(tutor=self.profile())

    def perform_create(self, serializer):
        services.ensure_editable(self.profile())
        serializer.save(tutor=self.profile())
        services.mark_changed_after_approval(self.profile(), "qualifications")
        services.refresh_draft_state(self.profile())

    def perform_update(self, serializer):
        services.ensure_editable(self.profile())
        # An edited qualification is no longer the one an administrator checked.
        serializer.save(verified=False, verified_by=None, verified_at=None)
        services.mark_changed_after_approval(self.profile(), "qualifications")

    def perform_destroy(self, instance):
        services.ensure_editable(self.profile())
        instance.delete()
        services.mark_changed_after_approval(self.profile(), "qualifications")
        services.refresh_draft_state(self.profile())


class MyDocumentViewSet(TutorOwnedMixin, mixins.CreateModelMixin, mixins.ListModelMixin, mixins.DestroyModelMixin, viewsets.GenericViewSet):
    serializer_class = DocumentSerializer
    pagination_class = None

    def get_queryset(self):
        return TutorDocument.objects.filter(tutor=self.profile())

    def perform_create(self, serializer):
        services.ensure_editable(self.profile())
        f = serializer.validated_data["file"]
        serializer.save(
            tutor=self.profile(),
            original_name=f.name[:255],
            content_type=(mimetypes.guess_type(f.name)[0] or "")[:100],
            size=f.size,
        )
        services.mark_changed_after_approval(self.profile(), "credential documents")
        services.refresh_draft_state(self.profile())

    def perform_destroy(self, instance):
        services.ensure_editable(self.profile())
        if instance.status == TutorDocument.Status.VERIFIED:
            from rest_framework.exceptions import ValidationError

            raise ValidationError({"detail": "A verified document cannot be removed. Contact the administrator."})
        instance.file.delete(save=False)
        instance.delete()
        services.refresh_draft_state(self.profile())


class MyAvailabilityViewSet(TutorOwnedMixin, viewsets.ModelViewSet):
    serializer_class = AvailabilitySerializer
    pagination_class = None

    def get_queryset(self):
        return TutorAvailability.objects.filter(tutor=self.profile())

    def perform_create(self, serializer):
        if self.profile().status == TutorProfile.Status.SUSPENDED:
            from rest_framework.exceptions import PermissionDenied

            raise PermissionDenied("Your profile is suspended.")
        serializer.save(tutor=self.profile())


# ---------------------------------------------------------------- private document download

class DocumentDownloadView(APIView):
    """The only way to read a credential file: owner or administrator, authenticated, never cached."""

    permission_classes = [IsAuthenticated]

    def get(self, request, pk):
        try:
            doc = TutorDocument.objects.select_related("tutor").get(pk=pk)
        except TutorDocument.DoesNotExist:
            raise Http404
        user = request.user
        is_owner = user.role == "tutor" and doc.tutor.user_id == user.id
        if not (is_owner or (user.role == "admin" and user.is_active)):
            raise Http404  # do not reveal that the document exists
        if user.role == "admin":
            log(user, "document_viewed", doc, f"tutor={doc.tutor_id}")
        response = FileResponse(
            doc.file.open("rb"),
            as_attachment=True,
            filename=doc.original_name,
            content_type=doc.content_type or "application/octet-stream",
        )
        response["Cache-Control"] = "private, no-store"
        response["X-Content-Type-Options"] = "nosniff"
        return response


# ---------------------------------------------------------------- administrator

class AdminTutorViewSet(viewsets.ReadOnlyModelViewSet):
    permission_classes = [IsAdminRole]
    filterset_fields = ["status", "gender", "location", "has_unreviewed_changes"]
    search_fields = ["display_name", "user__email", "user__full_name", "user__phone"]
    ordering_fields = ["submitted_at", "created_at", "display_name", "reviewed_at"]
    ordering = ["-submitted_at", "-created_at"]

    def get_queryset(self):
        qs = TutorProfile.objects.select_related("user", "location", "reviewed_by").prefetch_related("documents")
        if self.action == "retrieve":
            qs = qs.prefetch_related("subjects", "grade_levels", "qualifications", "availability", "documents__qualification", "documents__reviewed_by")
        return qs

    def get_serializer_class(self):
        return AdminTutorDetailSerializer if self.action == "retrieve" else AdminTutorListSerializer

    def _decide(self, request, action_name):
        serializer = ReviewNoteSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        profile = services.apply_action(self.get_object(), action_name, request.user, serializer.validated_data.get("note", ""))
        return Response(AdminTutorDetailSerializer(self.get_queryset().get(pk=profile.pk), context={"request": request}).data)

    @action(detail=True, methods=["post"])
    def approve(self, request, pk=None):
        return self._decide(request, "approve")

    @action(detail=True, methods=["post"])
    def reject(self, request, pk=None):
        return self._decide(request, "reject")

    @action(detail=True, methods=["post"], url_path="request-info")
    def request_info(self, request, pk=None):
        return self._decide(request, "request_info")

    @action(detail=True, methods=["post"])
    def suspend(self, request, pk=None):
        return self._decide(request, "suspend")

    @action(detail=True, methods=["post"])
    def reinstate(self, request, pk=None):
        return self._decide(request, "reinstate")


class AdminDocumentViewSet(mixins.ListModelMixin, mixins.RetrieveModelMixin, viewsets.GenericViewSet):
    permission_classes = [IsAdminRole]
    serializer_class = AdminDocumentSerializer
    queryset = TutorDocument.objects.select_related("tutor", "qualification", "reviewed_by")
    filterset_fields = ["status", "tutor", "doc_type"]
    search_fields = ["tutor__display_name", "original_name"]
    ordering = ["-uploaded_at"]

    @action(detail=True, methods=["post"])
    def review(self, request, pk=None):
        doc = self.get_object()
        serializer = DocumentReviewSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        old = doc.status
        doc.status = serializer.validated_data["status"]
        doc.reviewer_note = serializer.validated_data.get("note", "")[:500]
        doc.reviewed_by = request.user
        doc.reviewed_at = timezone.now()
        doc.save()
        if doc.qualification_id:
            q = doc.qualification
            q.verified = doc.status == TutorDocument.Status.VERIFIED
            q.verified_by = request.user if q.verified else None
            q.verified_at = timezone.now() if q.verified else None
            q.save()
        record_status(doc, old, doc.status, request.user, doc.reviewer_note)
        log(request.user, f"document_{doc.status}", doc, f"tutor={doc.tutor_id}")
        notify(doc.tutor.user, "A credential document was reviewed", "Open My Credentials to see the result.", "/tutor/credentials", "tutor")
        return Response(AdminDocumentSerializer(doc).data)


class AdminQualificationViewSet(mixins.RetrieveModelMixin, viewsets.GenericViewSet):
    permission_classes = [IsAdminRole]
    serializer_class = AdminQualificationSerializer
    queryset = TutorQualification.objects.select_related("tutor")

    @action(detail=True, methods=["post"])
    def verify(self, request, pk=None):
        q = self.get_object()
        value = bool(request.data.get("verified", True))
        q.verified = value
        q.verified_by = request.user if value else None
        q.verified_at = timezone.now() if value else None
        q.save()
        log(request.user, "qualification_verified" if value else "qualification_unverified", q, f"tutor={q.tutor_id}")
        return Response(AdminQualificationSerializer(q).data)
