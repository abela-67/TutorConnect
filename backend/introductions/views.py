from rest_framework import mixins, status, viewsets
from rest_framework.decorators import action
from rest_framework.response import Response

from accounts.permissions import IsAdminRole, IsParent
from audit.services import log, record_status

from . import services
from .models import Introduction
from .serializers import AdminIntroductionSerializer, ConsentSerializer, IntroStatusSerializer, ParentIntroductionSerializer


class AdminIntroductionViewSet(viewsets.ModelViewSet):
    """Only administrators can create or change introductions."""

    permission_classes = [IsAdminRole]
    serializer_class = AdminIntroductionSerializer
    filterset_fields = ["status", "parent_request", "tutor", "job", "responsible_admin"]
    search_fields = ["tutor__display_name", "parent_request__parent__full_name", "parent_request__contact_name"]
    ordering = ["-created_at"]
    http_method_names = ["get", "post", "patch", "head", "options"]

    def get_queryset(self):
        return Introduction.objects.select_related("parent_request", "parent_request__parent", "tutor", "job", "responsible_admin")

    def perform_create(self, serializer):
        intro = serializer.save(responsible_admin=serializer.validated_data.get("responsible_admin") or self.request.user)
        record_status(intro, "", intro.status, self.request.user, "Introduction created")
        log(self.request.user, "introduction_created", intro, f"request={intro.parent_request_id} tutor={intro.tutor_id}")

    def perform_update(self, serializer):
        intro = serializer.save()
        log(self.request.user, "introduction_updated", intro)

    @action(detail=True, methods=["post"], url_path="set-status")
    def set_status(self, request, pk=None):
        serializer = IntroStatusSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        d = serializer.validated_data
        intro = services.change_intro_status(
            self.get_object(), d["status"], request.user,
            note=d.get("note", ""), outcome_notes=d.get("outcome_notes"), introduced_on=d.get("introduced_on"),
        )
        return Response(self.get_serializer(intro).data)

    @action(detail=True, methods=["post"])
    def consent(self, request, pk=None):
        serializer = ConsentSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        intro = services.record_consent(self.get_object(), serializer.validated_data["party"], serializer.validated_data["agreed"], request.user)
        return Response(self.get_serializer(intro).data)

    @action(detail=True, methods=["post"], url_path="share-contact")
    def share_contact(self, request, pk=None):
        intro = services.share_contact(self.get_object(), request.user)
        return Response(self.get_serializer(intro).data, status=status.HTTP_200_OK)


class ParentIntroductionViewSet(mixins.ListModelMixin, mixins.RetrieveModelMixin, viewsets.GenericViewSet):
    """Introductions for the parent's own requests only; cancelled ones are hidden."""

    permission_classes = [IsParent]
    serializer_class = ParentIntroductionSerializer

    def get_queryset(self):
        return (
            Introduction.objects.filter(parent_request__parent=self.request.user)
            .exclude(status=Introduction.Status.CANCELLED)
            .select_related("parent_request", "tutor", "tutor__user", "tutor__location")
            .prefetch_related("tutor__subjects", "tutor__grade_levels", "tutor__qualifications")
        )
