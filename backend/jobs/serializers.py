from rest_framework import serializers

from audit.serializers import StatusHistorySerializer
from audit.services import history_for
from catalog.serializers import GradeLevelSerializer, LocationSerializer, SubjectSerializer
from config.mixins import NamedFKMixin
from tutors.serializers import TutorListSerializer

from .models import JobApplication, TutoringJob
from .services import is_accepting
from .validators import validate_public_text

PUBLIC_TEXT_FIELDS = (
    "title", "preferred_schedule", "frequency", "duration", "payment_note",
    "required_qualifications", "additional_requirements",
)


class TutorJobSerializer(serializers.ModelSerializer):
    """What approved tutors see. An explicit allow-list: no parent data, no request link, no internal notes."""

    reference = serializers.CharField(read_only=True)
    subject = SubjectSerializer(read_only=True)
    grade_level = GradeLevelSerializer(read_only=True)
    location = LocationSerializer(read_only=True)
    status_display = serializers.CharField(source="get_status_display", read_only=True)
    accepting_applications = serializers.SerializerMethodField()
    my_application = serializers.SerializerMethodField()

    class Meta:
        model = TutoringJob
        fields = [
            "id", "reference", "title", "subject", "grade_level", "location", "teaching_mode", "preferred_schedule",
            "frequency", "duration", "payment_amount", "payment_note", "required_qualifications",
            "additional_requirements", "application_deadline", "status", "status_display", "published_at",
            "accepting_applications", "my_application",
        ]

    def get_accepting_applications(self, obj):
        return is_accepting(obj)

    def get_my_application(self, obj):
        tutor = self.context["request"].user.tutor_profile
        app = next((a for a in obj.applications.all() if a.tutor_id == tutor.pk), None)
        return {"id": app.id, "status": app.status} if app else None


class AdminJobSerializer(NamedFKMixin, serializers.ModelSerializer):
    named_fks = (("subject", "subject_name"), ("grade_level", "grade_level_name"), ("location", "location_name"))
    reference = serializers.CharField(read_only=True)
    status_display = serializers.CharField(source="get_status_display", read_only=True)
    source_request_reference = serializers.SerializerMethodField()
    application_count = serializers.SerializerMethodField()
    history = serializers.SerializerMethodField()

    class Meta:
        model = TutoringJob
        fields = [
            "id", "reference", "title", "subject", "grade_level", "location", "teaching_mode", "preferred_schedule",
            "frequency", "duration", "payment_amount", "payment_note", "required_qualifications",
            "additional_requirements", "application_deadline", "status", "status_display", "source_request",
            "source_request_reference", "internal_notes", "outcome", "published_at", "closed_at", "created_at",
            "updated_at", "application_count", "history",
        ]
        read_only_fields = ["status", "published_at", "closed_at", "created_at", "updated_at", "outcome"]

    def get_source_request_reference(self, obj):
        return obj.source_request.reference if obj.source_request_id else None

    def get_application_count(self, obj):
        return len(obj.applications.all())

    def get_history(self, obj):
        view = self.context.get("view")
        if view and getattr(view, "action", "") == "retrieve":
            return StatusHistorySerializer(history_for(obj), many=True).data
        return []

    def validate(self, attrs):
        for name in PUBLIC_TEXT_FIELDS:
            if name in attrs:
                try:
                    validate_public_text(attrs[name])
                except serializers.ValidationError as exc:
                    raise serializers.ValidationError({name: exc.detail})
        if attrs.get("payment_amount") is not None and attrs["payment_amount"] < 0:
            raise serializers.ValidationError({"payment_amount": "Payment cannot be negative."})
        return attrs


class ApplyJobSerializer(serializers.Serializer):
    message = serializers.CharField(required=False, allow_blank=True, max_length=500)

    def validate_message(self, value):
        return value.strip()


class TutorApplicationSerializer(serializers.ModelSerializer):
    """A tutor's own application, with the job summary (still without any parent data)."""

    job = TutorJobSerializer(read_only=True)
    status_display = serializers.CharField(source="get_status_display", read_only=True)

    class Meta:
        model = JobApplication
        fields = ["id", "job", "message", "status", "status_display", "created_at", "updated_at"]


class AdminApplicationSerializer(serializers.ModelSerializer):
    status_display = serializers.CharField(source="get_status_display", read_only=True)
    job_title = serializers.CharField(source="job.title", read_only=True)
    job_reference = serializers.CharField(source="job.reference", read_only=True)
    job_status = serializers.CharField(source="job.status", read_only=True)
    tutor_profile = serializers.SerializerMethodField()
    fit = serializers.SerializerMethodField()

    class Meta:
        model = JobApplication
        fields = [
            "id", "job", "job_title", "job_reference", "job_status", "tutor", "tutor_profile", "message",
            "status", "status_display", "admin_notes", "created_at", "updated_at", "fit",
        ]
        read_only_fields = ["job", "tutor", "message", "status", "created_at", "updated_at"]

    def get_tutor_profile(self, obj):
        data = TutorListSerializer(obj.tutor, context=self.context).data
        data["verified_documents"] = sum(1 for d in obj.tutor.documents.all() if d.status == "verified")
        data["has_unreviewed_changes"] = obj.tutor.has_unreviewed_changes
        return data

    def get_fit(self, obj):
        """Comparison against the job's own requirements, to help administrators compare candidates."""
        job, tutor = obj.job, obj.tutor
        subj = bool(job.subject_id) and any(s.pk == job.subject_id for s in tutor.subjects.all())
        grade = bool(job.grade_level_id) and any(g.pk == job.grade_level_id for g in tutor.grade_levels.all())
        mode_ok = job.teaching_mode in ("", "either") or tutor.teaching_mode in ("both", job.teaching_mode)
        loc = bool(job.location_id) and tutor.location_id == job.location_id
        return {"subject": subj, "grade_level": grade, "teaching_mode": mode_ok, "same_location": loc}


class SetApplicationStatusSerializer(serializers.Serializer):
    status = serializers.ChoiceField(choices=["under_review", "shortlisted", "selected", "not_selected"])
    note = serializers.CharField(required=False, allow_blank=True, max_length=500)
    admin_notes = serializers.CharField(required=False, allow_blank=True)


class SetJobStatusSerializer(serializers.Serializer):
    status = serializers.ChoiceField(choices=[c for c in TutoringJob.Status.choices if c[0] != "draft"])
    note = serializers.CharField(required=False, allow_blank=True, max_length=500)


class FinalizeSerializer(serializers.Serializer):
    outcome = serializers.CharField(required=False, allow_blank=True)
