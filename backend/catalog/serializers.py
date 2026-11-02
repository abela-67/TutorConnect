from rest_framework import serializers

from .models import GradeLevel, Location, Subject


class LocationSerializer(serializers.ModelSerializer):
    label = serializers.SerializerMethodField()

    class Meta:
        model = Location
        fields = ["id", "country", "city", "area", "label", "is_active"]

    def get_label(self, obj):
        return str(obj)


class SubjectSerializer(serializers.ModelSerializer):
    class Meta:
        model = Subject
        fields = ["id", "name", "is_active"]


class GradeLevelSerializer(serializers.ModelSerializer):
    class Meta:
        model = GradeLevel
        fields = ["id", "name", "order", "is_active"]
