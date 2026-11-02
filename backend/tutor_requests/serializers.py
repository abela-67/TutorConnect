from datetime import timedelta

from django.utils import timezone
from rest_framework import serializers

from accounts.models import User
from audit.serializers import StatusHistorySerializer
from audit.services import history_for
from config.mixins import NamedFKMixin
from tutors.models import TutorProfile

from .models import ParentRequest

NAMED = (
    ("subject", "subject_name"),
    ("grade_level", "grade_level_name"),
    ("location", "location_name"),
    ("preferred_tutor", "preferred_tutor_name"),
)


class ParentRequestCreateSerializer(serializers.ModelSerializer):
    """Minimal online form: subject, grade and teaching mode/location are required; everything else is optional."""

    teaching_mode = serializers.ChoiceField(choices=ParentRequest.Mode.choices)
    preferred_tutor = serializers.PrimaryKeyRelatedField(queryset=TutorProfile.objects.public(), required=False, allow_null=True)

    class Meta:
        model = ParentRequest
        fields = [
            "subject", "grade_level", "location", "teaching_mode", "preferred_tutor", "preferred_gender",
            "preferred_schedule", "budget_amount", "additional_requirements",
        ]
        extra_kwargs = {
            "subject": {"required": True, "allow_null": False},
            "grade_level": {"required": True, "allow_null": False},
            "location": {"required": False, "allow_null": True},
        }

    def validate_preferred_gender(self, value):
        if value and value not in ("male", "female"):
            raise serializers.ValidationError("Choose male, female, or leave blank.")
        return value

    def validate_budget_amount(self, value):
        if value is not None and value < 0:
            raise serializers.ValidationError("Budget cannot be negative.")
        return value

    def validate(self, attrs):
        if attrs["teaching_mode"] != "online" and not attrs.get("location"):
            raise serializers.ValidationError({"location": "Please choose a location for in-person lessons."})
        user = self.context["request"].user
        recent = ParentRequest.objects.filter(
            parent=user,
            subject=attrs["subject"],
            grade_level=attrs["grade_level"],
            preferred_tutor=attrs.get("preferred_tutor"),
            created_at__gte=timezone.now() - timedelta(seconds=60),
        )
        if recent.exists():
            raise serializers.ValidationError({"detail": "This request was just submitted. Please check My Requests."})
        return attrs

    def create(self, validated_data):
        return ParentRequest.objects.create(
            parent=self.context["request"].user,
            source=ParentRequest.Source.WEBSITE,
            status=ParentRequest.Status.NEW,
            **validated_data,
        )


class ParentRequestSerializer(NamedFKMixin, serializers.ModelSerializer):
    """What a parent sees about their own request. No internal notes, assignment or contact fields."""

    named_fks = NAMED
    reference = serializers.CharField(read_only=True)
    status_display = serializers.CharField(source="get_status_display", read_only=True)
    introductions = serializers.SerializerMethodField()

    class Meta:
        model = ParentRequest
        fields = [
            "id", "reference", "created_at", "updated_at", "status", "status_display", "subject", "grade_level",
            "location", "teaching_mode", "preferred_tutor", "preferred_gender", "preferred_schedule",
            "budget_amount", "additional_requirements", "latest_update", "is_open", "introductions",
        ]
        read_only_fields = fields

    def get_introductions(self, obj):
        return obj.introductions.exclude(status="cancelled").count()


class AdminRequestSerializer(NamedFKMixin, serializers.ModelSerializer):
    named_fks = NAMED + (("assigned_to", "assigned_to_name"),)
    reference = serializers.CharField(read_only=True)
    status_display = serializers.CharField(source="get_status_display", read_only=True)
    source_display = serializers.CharField(source="get_source_display", read_only=True)
    is_draft = serializers.BooleanField(write_only=True, required=False, default=False)
    parent_info = serializers.SerializerMethodField()
    jobs = serializers.SerializerMethodField()
    introductions = serializers.SerializerMethodField()
    history = serializers.SerializerMethodField()
    applicant_count = serializers.SerializerMethodField()

    class Meta:
        model = ParentRequest
        fields = [
            "id", "reference", "created_at", "updated_at", "source", "source_display", "status", "status_display",
            "parent", "parent_info", "contact_name", "contact_phone", "contact_email", "subject", "grade_level",
            "location", "teaching_mode", "preferred_tutor", "preferred_gender", "preferred_schedule", "budget_amount",
            "additional_requirements", "internal_notes", "assigned_to", "outcome", "latest_update", "is_open",
            "is_draft", "jobs", "introductions", "history", "applicant_count",
        ]
        read_only_fields = ["status", "parent", "created_at", "updated_at"]

    def get_parent_info(self, obj):
        if not obj.parent_id:
            return None
        p = obj.parent
        return {"id": p.id, "full_name": p.full_name, "email": p.email, "phone": p.phone}

    def get_jobs(self, obj):
        return [{"id": j.id, "reference": j.reference, "title": j.title, "status": j.status} for j in obj.jobs.all()]

    def get_introductions(self, obj):
        return [
            {"id": i.id, "tutor": i.tutor_id, "tutor_name": i.tutor.display_name, "status": i.status}
            for i in obj.introductions.select_related("tutor")
        ]

    def get_history(self, obj):
        if self.context.get("view") and getattr(self.context["view"], "action", "") == "retrieve":
            return StatusHistorySerializer(history_for(obj), many=True).data
        return []

    def get_applicant_count(self, obj):
        return sum(j.applications.count() for j in obj.jobs.all())

    def create(self, validated_data):
        is_draft = validated_data.pop("is_draft", False)
        validated_data.setdefault("source", ParentRequest.Source.TELEPHONE)
        validated_data["status"] = ParentRequest.Status.DRAFT if is_draft else ParentRequest.Status.NEW
        return super().create(validated_data)

    def update(self, instance, validated_data):
        validated_data.pop("is_draft", None)
        return super().update(instance, validated_data)

    def validate_assigned_to(self, value):
        if value and value.role != User.Role.ADMIN:
            raise serializers.ValidationError("Requests can only be assigned to administrators.")
        return value

    def validate_budget_amount(self, value):
        if value is not None and value < 0:
            raise serializers.ValidationError("Budget cannot be negative.")
        return value


class SetStatusSerializer(serializers.Serializer):
    status = serializers.ChoiceField(choices=ParentRequest.Status.choices)
    latest_update = serializers.CharField(required=False, allow_blank=True, max_length=300)
    outcome = serializers.CharField(required=False, allow_blank=True)
    note = serializers.CharField(required=False, allow_blank=True, max_length=500)


class AssignSerializer(serializers.Serializer):
    admin = serializers.PrimaryKeyRelatedField(queryset=User.objects.filter(role=User.Role.ADMIN, is_active=True), allow_null=True)
