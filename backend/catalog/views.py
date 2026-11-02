from rest_framework import viewsets
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView

from accounts.permissions import IsAdminRole
from audit.services import log

from .models import GradeLevel, Location, Subject
from .serializers import GradeLevelSerializer, LocationSerializer, SubjectSerializer

# Choice lists shared with the front end so labels live in one place.
GENDERS = [("male", "Male"), ("female", "Female"), ("other", "Other")]
TEACHING_MODES = [("online", "Online"), ("in_person", "In person"), ("both", "Both online and in person")]
REQUEST_MODES = [("online", "Online"), ("in_person", "In person"), ("either", "Either")]
WEEKDAYS = [(0, "Monday"), (1, "Tuesday"), (2, "Wednesday"), (3, "Thursday"), (4, "Friday"), (5, "Saturday"), (6, "Sunday")]


class ReferenceDataView(APIView):
    """Public lookup lists used by search filters and forms. Subjects/locations/grades are database records."""

    permission_classes = [AllowAny]
    authentication_classes = []

    def get(self, request):
        return Response(
            {
                "subjects": SubjectSerializer(Subject.objects.filter(is_active=True), many=True).data,
                "grade_levels": GradeLevelSerializer(GradeLevel.objects.filter(is_active=True), many=True).data,
                "locations": LocationSerializer(Location.objects.filter(is_active=True), many=True).data,
                "genders": [{"value": v, "label": l} for v, l in GENDERS],
                "teaching_modes": [{"value": v, "label": l} for v, l in TEACHING_MODES],
                "request_modes": [{"value": v, "label": l} for v, l in REQUEST_MODES],
                "weekdays": [{"value": v, "label": l} for v, l in WEEKDAYS],
            }
        )


class _AdminCatalogViewSet(viewsets.ModelViewSet):
    """Admin-managed reference data. Items are deactivated rather than deleted so history stays intact."""

    permission_classes = [IsAdminRole]
    http_method_names = ["get", "post", "patch", "head", "options"]
    pagination_class = None
    audit_prefix = ""

    def perform_create(self, serializer):
        obj = serializer.save()
        log(self.request.user, f"{self.audit_prefix}_created", obj, str(obj))

    def perform_update(self, serializer):
        obj = serializer.save()
        log(self.request.user, f"{self.audit_prefix}_updated", obj, str(obj))


class AdminSubjectViewSet(_AdminCatalogViewSet):
    queryset = Subject.objects.all()
    serializer_class = SubjectSerializer
    audit_prefix = "subject"


class AdminGradeLevelViewSet(_AdminCatalogViewSet):
    queryset = GradeLevel.objects.all()
    serializer_class = GradeLevelSerializer
    audit_prefix = "grade_level"


class AdminLocationViewSet(_AdminCatalogViewSet):
    queryset = Location.objects.all()
    serializer_class = LocationSerializer
    audit_prefix = "location"
