from datetime import timedelta

from django.utils import timezone
from rest_framework import serializers

from accounts.models import User
from audit.serializers import StatusHistorySerializer
from audit.services import history_for
from config.mixins import NamedFKMixin
from tutors.models import TutorProfile

from .models import PersonalInquiry


class InquiryCreateSerializer(serializers.ModelSerializer):
    about_tutor = serializers.PrimaryKeyRelatedField(queryset=TutorProfile.objects.public(), required=False, allow_null=True)

    class Meta:
        model = PersonalInquiry
        fields = ["category", "message", "preferred_response", "about_tutor"]
        extra_kwargs = {"category": {"required": False}, "preferred_response": {"required": False}}

    def validate_message(self, value):
        value = value.strip()
        if len(value) < 5:
            raise serializers.ValidationError("Please write a short message.")
        return value

    def validate(self, attrs):
        user = self.context["request"].user
        if PersonalInquiry.objects.filter(parent=user, message=attrs["message"], created_at__gte=timezone.now() - timedelta(minutes=2)).exists():
            raise serializers.ValidationError({"detail": "This message was just sent."})
        return attrs

    def create(self, validated_data):
        return PersonalInquiry.objects.create(parent=self.context["request"].user, **validated_data)


class ParentInquirySerializer(NamedFKMixin, serializers.ModelSerializer):
    """The parent's own view: includes the administrator's reply but never internal notes."""

    named_fks = (("about_tutor", "about_tutor_name"),)
    reference = serializers.CharField(read_only=True)
    category_display = serializers.CharField(source="get_category_display", read_only=True)
    status_display = serializers.CharField(source="get_status_display", read_only=True)

    class Meta:
        model = PersonalInquiry
        fields = [
            "id", "reference", "category", "category_display", "message", "preferred_response", "about_tutor",
            "status", "status_display", "admin_response", "created_at", "updated_at",
        ]
        read_only_fields = fields


class AdminInquirySerializer(NamedFKMixin, serializers.ModelSerializer):
    named_fks = (("about_tutor", "about_tutor_name"), ("assigned_to", "assigned_to_name"))
    reference = serializers.CharField(read_only=True)
    category_display = serializers.CharField(source="get_category_display", read_only=True)
    status_display = serializers.CharField(source="get_status_display", read_only=True)
    parent_info = serializers.SerializerMethodField()
    converted_request_reference = serializers.SerializerMethodField()
    history = serializers.SerializerMethodField()

    class Meta:
        model = PersonalInquiry
        fields = [
            "id", "reference", "parent", "parent_info", "category", "category_display", "message", "preferred_response",
            "about_tutor", "status", "status_display", "assigned_to", "internal_notes", "admin_response",
            "converted_request", "converted_request_reference", "created_at", "updated_at", "history",
        ]
        read_only_fields = ["parent", "category", "message", "preferred_response", "about_tutor", "status", "converted_request", "created_at", "updated_at"]

    def get_parent_info(self, obj):
        p = obj.parent
        return {"id": p.id, "full_name": p.full_name, "email": p.email, "phone": p.phone}

    def get_converted_request_reference(self, obj):
        return obj.converted_request.reference if obj.converted_request_id else None

    def get_history(self, obj):
        view = self.context.get("view")
        if view and getattr(view, "action", "") == "retrieve":
            return StatusHistorySerializer(history_for(obj), many=True).data
        return []

    def validate_assigned_to(self, value):
        if value and value.role != User.Role.ADMIN:
            raise serializers.ValidationError("Inquiries can only be assigned to administrators.")
        return value


class InquiryStatusSerializer(serializers.Serializer):
    status = serializers.ChoiceField(choices=PersonalInquiry.Status.choices)
    note = serializers.CharField(required=False, allow_blank=True, max_length=500)


class RespondSerializer(serializers.Serializer):
    response = serializers.CharField(max_length=3000)
    status = serializers.ChoiceField(choices=PersonalInquiry.Status.choices, required=False)
