import os

from django.conf import settings
from rest_framework import serializers

from catalog.models import GradeLevel, Subject
from catalog.serializers import GradeLevelSerializer, LocationSerializer, SubjectSerializer

from .models import TutorAvailability, TutorDocument, TutorProfile, TutorQualification

ALLOWED_DOC_EXTENSIONS = {".pdf", ".jpg", ".jpeg", ".png"}
MAGIC_BYTES = {
    ".pdf": (b"%PDF",),
    ".jpg": (b"\xff\xd8\xff",),
    ".jpeg": (b"\xff\xd8\xff",),
    ".png": (b"\x89PNG\r\n\x1a\n",),
}


def _photo_url(obj, request):
    if not obj.photo:
        return None
    url = obj.photo.url
    return request.build_absolute_uri(url) if request else url


# ---------------------------------------------------------------- public directory

class PublicQualificationSerializer(serializers.ModelSerializer):
    class Meta:
        model = TutorQualification
        fields = ["id", "level", "title", "institution", "field_of_study", "year", "verified"]


class PublicAvailabilitySerializer(serializers.ModelSerializer):
    class Meta:
        model = TutorAvailability
        fields = ["id", "weekday", "start_time", "end_time"]


class _PublicBase(serializers.ModelSerializer):
    """Public representation. Deliberately has NO email, phone, documents, notes or review data."""

    subjects = SubjectSerializer(many=True, read_only=True)
    grade_levels = GradeLevelSerializer(many=True, read_only=True)
    location = LocationSerializer(read_only=True)
    gender = serializers.SerializerMethodField()
    photo = serializers.SerializerMethodField()
    verified_qualifications = serializers.SerializerMethodField()

    def get_gender(self, obj):
        return obj.gender if (obj.show_gender and obj.gender) else None

    def get_photo(self, obj):
        return _photo_url(obj, self.context.get("request"))

    def get_verified_qualifications(self, obj):
        return sum(1 for q in obj.qualifications.all() if q.verified)


class TutorListSerializer(_PublicBase):
    class Meta:
        model = TutorProfile
        fields = [
            "id", "display_name", "photo", "gender", "location", "subjects", "grade_levels",
            "years_experience", "teaching_mode", "rate_amount", "rate_unit", "verified_qualifications",
        ]


class TutorDetailSerializer(_PublicBase):
    qualifications = PublicQualificationSerializer(many=True, read_only=True)
    availability = PublicAvailabilitySerializer(many=True, read_only=True)
    verification = serializers.SerializerMethodField()

    class Meta:
        model = TutorProfile
        fields = [
            "id", "display_name", "photo", "bio", "gender", "location", "subjects", "grade_levels",
            "years_experience", "teaching_methods", "teaching_mode", "languages", "rate_amount", "rate_unit",
            "qualifications", "availability", "verified_qualifications", "verification",
        ]

    def get_verification(self, obj):
        # Be precise about what was checked: only qualifications an administrator marked verified.
        return {
            "profile_approved": True,
            "verified_qualifications": self.get_verified_qualifications(obj),
            "total_qualifications": len(obj.qualifications.all()),
            "has_changes_awaiting_review": obj.has_unreviewed_changes,
            "reviewed_at": obj.reviewed_at,
        }


# ---------------------------------------------------------------- tutor self-service

class TutorProfileSelfSerializer(serializers.ModelSerializer):
    subjects = serializers.PrimaryKeyRelatedField(many=True, queryset=Subject.objects.filter(is_active=True), required=False)
    grade_levels = serializers.PrimaryKeyRelatedField(many=True, queryset=GradeLevel.objects.filter(is_active=True), required=False)
    email = serializers.EmailField(source="user.email", read_only=True)
    phone = serializers.CharField(source="user.phone", read_only=True)
    photo = serializers.SerializerMethodField()
    completeness = serializers.SerializerMethodField()
    missing = serializers.SerializerMethodField()
    status_display = serializers.CharField(source="get_status_display", read_only=True)

    class Meta:
        model = TutorProfile
        fields = [
            "id", "display_name", "photo", "bio", "gender", "show_gender", "location", "years_experience",
            "teaching_methods", "teaching_mode", "languages", "rate_amount", "rate_unit", "subjects", "grade_levels",
            "status", "status_display", "status_note", "has_unreviewed_changes", "submitted_at", "reviewed_at",
            "email", "phone", "completeness", "missing",
        ]
        read_only_fields = ["status", "status_note", "has_unreviewed_changes", "submitted_at", "reviewed_at"]

    def get_photo(self, obj):
        return _photo_url(obj, self.context.get("request"))

    def get_completeness(self, obj):
        return obj.completeness()

    def get_missing(self, obj):
        return obj.missing_for_submission()

    def validate_languages(self, value):
        if not isinstance(value, list) or not all(isinstance(v, str) and len(v) <= 50 for v in value):
            raise serializers.ValidationError("Provide a list of language names.")
        return value[:15]

    def validate_rate_amount(self, value):
        if value is not None and value < 0:
            raise serializers.ValidationError("Rate cannot be negative.")
        return value

    def validate_years_experience(self, value):
        if value > 70:
            raise serializers.ValidationError("Please enter a realistic number of years.")
        return value


class PhotoSerializer(serializers.Serializer):
    photo = serializers.ImageField()

    def validate_photo(self, value):
        if value.size > settings.MAX_PHOTO_SIZE_MB * 1024 * 1024:
            raise serializers.ValidationError(f"Photo must be {settings.MAX_PHOTO_SIZE_MB} MB or smaller.")
        return value


class QualificationSerializer(serializers.ModelSerializer):
    class Meta:
        model = TutorQualification
        fields = ["id", "level", "title", "institution", "field_of_study", "year", "verified"]
        read_only_fields = ["verified"]

    def validate_year(self, value):
        if value is not None and not (1950 <= value <= 2100):
            raise serializers.ValidationError("Enter a valid year.")
        return value


class DocumentSerializer(serializers.ModelSerializer):
    """What the tutor (owner) sees. Never exposes a file URL; downloads go through an authorised endpoint."""

    file = serializers.FileField(write_only=True)
    qualification = serializers.PrimaryKeyRelatedField(queryset=TutorQualification.objects.all(), required=False, allow_null=True)

    class Meta:
        model = TutorDocument
        fields = ["id", "doc_type", "qualification", "file", "original_name", "size", "status", "reviewer_note", "uploaded_at"]
        read_only_fields = ["original_name", "size", "status", "reviewer_note", "uploaded_at"]

    def validate_qualification(self, value):
        tutor = self.context["request"].user.tutor_profile
        if value is not None and value.tutor_id != tutor.pk:
            raise serializers.ValidationError("Invalid qualification.")
        return value

    def validate_file(self, f):
        ext = os.path.splitext(f.name)[1].lower()
        if ext not in ALLOWED_DOC_EXTENSIONS:
            raise serializers.ValidationError("Only PDF, JPG and PNG files are accepted.")
        if f.size > settings.MAX_DOCUMENT_SIZE_MB * 1024 * 1024:
            raise serializers.ValidationError(f"File must be {settings.MAX_DOCUMENT_SIZE_MB} MB or smaller.")
        if f.size == 0:
            raise serializers.ValidationError("The file is empty.")
        head = f.read(8)
        f.seek(0)
        if not any(head.startswith(sig) for sig in MAGIC_BYTES[ext]):
            raise serializers.ValidationError("The file content does not match its type.")
        return f


class AvailabilitySerializer(serializers.ModelSerializer):
    class Meta:
        model = TutorAvailability
        fields = ["id", "weekday", "start_time", "end_time"]

    def validate(self, attrs):
        start = attrs.get("start_time", getattr(self.instance, "start_time", None))
        end = attrs.get("end_time", getattr(self.instance, "end_time", None))
        if start and end and end <= start:
            raise serializers.ValidationError({"end_time": "End time must be after start time."})
        return attrs


# ---------------------------------------------------------------- administrator views

class AdminDocumentSerializer(serializers.ModelSerializer):
    tutor_name = serializers.CharField(source="tutor.display_name", read_only=True)
    qualification_title = serializers.SerializerMethodField()
    reviewed_by_name = serializers.SerializerMethodField()

    class Meta:
        model = TutorDocument
        fields = [
            "id", "tutor", "tutor_name", "doc_type", "qualification", "qualification_title", "original_name",
            "content_type", "size", "status", "reviewer_note", "reviewed_by_name", "reviewed_at", "uploaded_at",
        ]
        read_only_fields = fields

    def get_qualification_title(self, obj):
        return obj.qualification.title if obj.qualification_id else None

    def get_reviewed_by_name(self, obj):
        return obj.reviewed_by.full_name if obj.reviewed_by_id else None


class AdminQualificationSerializer(serializers.ModelSerializer):
    class Meta:
        model = TutorQualification
        fields = ["id", "level", "title", "institution", "field_of_study", "year", "verified", "verified_at"]
        read_only_fields = fields


class AdminTutorListSerializer(serializers.ModelSerializer):
    email = serializers.EmailField(source="user.email", read_only=True)
    phone = serializers.CharField(source="user.phone", read_only=True)
    account_active = serializers.BooleanField(source="user.is_active", read_only=True)
    status_display = serializers.CharField(source="get_status_display", read_only=True)
    location_name = serializers.SerializerMethodField()
    pending_documents = serializers.SerializerMethodField()

    class Meta:
        model = TutorProfile
        fields = [
            "id", "display_name", "email", "phone", "account_active", "status", "status_display", "location_name",
            "has_unreviewed_changes", "submitted_at", "reviewed_at", "created_at", "pending_documents",
        ]

    def get_location_name(self, obj):
        return str(obj.location) if obj.location_id else None

    def get_pending_documents(self, obj):
        return sum(1 for d in obj.documents.all() if d.status == "pending")


class AdminTutorDetailSerializer(AdminTutorListSerializer):
    subjects = SubjectSerializer(many=True, read_only=True)
    grade_levels = GradeLevelSerializer(many=True, read_only=True)
    qualifications = AdminQualificationSerializer(many=True, read_only=True)
    documents = AdminDocumentSerializer(many=True, read_only=True)
    availability = PublicAvailabilitySerializer(many=True, read_only=True)
    history = serializers.SerializerMethodField()
    reviewed_by_name = serializers.SerializerMethodField()
    gender = serializers.CharField(read_only=True)

    class Meta(AdminTutorListSerializer.Meta):
        fields = AdminTutorListSerializer.Meta.fields + [
            "bio", "gender", "show_gender", "years_experience", "teaching_methods", "teaching_mode", "languages",
            "rate_amount", "rate_unit", "subjects", "grade_levels", "qualifications", "documents", "availability",
            "status_note", "reviewed_by_name", "history",
        ]

    def get_reviewed_by_name(self, obj):
        return obj.reviewed_by.full_name if obj.reviewed_by_id else None

    def get_history(self, obj):
        from audit.serializers import StatusHistorySerializer
        from audit.services import history_for

        return StatusHistorySerializer(history_for(obj), many=True).data


class ReviewNoteSerializer(serializers.Serializer):
    note = serializers.CharField(required=False, allow_blank=True, max_length=500)


class DocumentReviewSerializer(serializers.Serializer):
    status = serializers.ChoiceField(choices=[("verified", "Verified"), ("rejected", "Rejected")])
    note = serializers.CharField(required=False, allow_blank=True, max_length=500)

    def validate(self, attrs):
        if attrs["status"] == "rejected" and not attrs.get("note", "").strip():
            raise serializers.ValidationError({"note": "Please explain why the document was rejected."})
        return attrs
