from rest_framework import serializers

from .models import AuditLog, StatusHistory


class AuditLogSerializer(serializers.ModelSerializer):
    actor_name = serializers.SerializerMethodField()

    class Meta:
        model = AuditLog
        fields = ["id", "created_at", "actor", "actor_name", "action", "entity_type", "entity_id", "detail"]

    def get_actor_name(self, obj):
        return obj.actor.full_name if obj.actor_id else "System"


class StatusHistorySerializer(serializers.ModelSerializer):
    changed_by_name = serializers.SerializerMethodField()

    class Meta:
        model = StatusHistory
        fields = ["id", "from_status", "to_status", "changed_by_name", "note", "created_at"]

    def get_changed_by_name(self, obj):
        return obj.changed_by.full_name if obj.changed_by_id else "System"
