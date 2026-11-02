from rest_framework import serializers

from audit.serializers import StatusHistorySerializer
from audit.services import history_for
from config.mixins import NamedFKMixin
from tutors.serializers import TutorListSerializer

from .models import Introduction


class AdminIntroductionSerializer(NamedFKMixin, serializers.ModelSerializer):
    named_fks = (("tutor", "tutor_name"), ("job", "job_title"), ("responsible_admin", "responsible_admin_name"))
    request_reference = serializers.CharField(source="parent_request.reference", read_only=True)
    status_display = serializers.CharField(source="get_status_display", read_only=True)
    history = serializers.SerializerMethodField()
    parent_name = serializers.SerializerMethodField()

    class Meta:
        model = Introduction
        fields = [
            "id", "parent_request", "request_reference", "parent_name", "tutor", "job", "responsible_admin", "status",
            "status_display", "parent_agreed", "parent_agreed_at", "tutor_agreed", "tutor_agreed_at", "contact_shared",
            "contact_shared_at", "introduced_on", "outcome_notes", "created_at", "updated_at", "history",
        ]
        read_only_fields = [
            "status", "parent_agreed", "parent_agreed_at", "tutor_agreed", "tutor_agreed_at", "contact_shared",
            "contact_shared_at", "created_at", "updated_at",
        ]

    def get_parent_name(self, obj):
        req = obj.parent_request
        return req.parent.full_name if req.parent_id else (req.contact_name or "Phone request")

    def get_history(self, obj):
        view = self.context.get("view")
        if view and getattr(view, "action", "") == "retrieve":
            return StatusHistorySerializer(history_for(obj), many=True).data
        return []

    def validate(self, attrs):
        if self.instance is None:
            tutor = attrs["tutor"]
            if not tutor.is_publicly_listed:
                raise serializers.ValidationError({"tutor": "Only approved, active tutors can be introduced."})
            req = attrs["parent_request"]
            if not req.is_open:
                raise serializers.ValidationError({"parent_request": "This request is closed."})
            job = attrs.get("job")
            if job and job.source_request_id and job.source_request_id != req.id:
                raise serializers.ValidationError({"job": "This job belongs to a different request."})
        else:
            for locked in ("parent_request", "tutor"):
                if locked in attrs and attrs[locked] != getattr(self.instance, locked):
                    raise serializers.ValidationError({locked: "This cannot be changed after the introduction is created."})
        return attrs


class IntroStatusSerializer(serializers.Serializer):
    status = serializers.ChoiceField(choices=Introduction.Status.choices)
    note = serializers.CharField(required=False, allow_blank=True, max_length=500)
    outcome_notes = serializers.CharField(required=False, allow_blank=True)
    introduced_on = serializers.DateField(required=False, allow_null=True)


class ConsentSerializer(serializers.Serializer):
    party = serializers.ChoiceField(choices=["parent", "tutor"])
    agreed = serializers.BooleanField()


class ParentIntroductionSerializer(serializers.ModelSerializer):
    """What a parent may see: the tutor's public profile summary, status and dates. Contact only after consent."""

    reference = serializers.CharField(source="parent_request.reference", read_only=True)
    status_display = serializers.CharField(source="get_status_display", read_only=True)
    tutor = TutorListSerializer(read_only=True)
    tutor_contact = serializers.SerializerMethodField()

    class Meta:
        model = Introduction
        fields = ["id", "reference", "status", "status_display", "tutor", "introduced_on", "contact_shared", "tutor_contact", "created_at"]

    def get_tutor_contact(self, obj):
        if not obj.contact_shared:
            return None
        user = obj.tutor.user
        return {"name": user.full_name, "phone": user.phone, "email": user.email}
