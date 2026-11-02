from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError as DjangoValidationError
from django.db import transaction
from rest_framework import serializers
from rest_framework_simplejwt.serializers import TokenObtainPairSerializer

from catalog.models import Location

from .models import ParentProfile, User


class UserSerializer(serializers.ModelSerializer):
    """The signed-in user's own data."""

    tutor_status = serializers.SerializerMethodField()
    preferred_contact = serializers.SerializerMethodField()
    default_location = serializers.SerializerMethodField()

    class Meta:
        model = User
        fields = ["id", "email", "full_name", "phone", "role", "tutor_status", "preferred_contact", "default_location"]
        read_only_fields = ["id", "email", "role"]

    def get_tutor_status(self, obj):
        profile = getattr(obj, "tutor_profile", None) if obj.role == "tutor" else None
        return profile.status if profile else None

    def get_preferred_contact(self, obj):
        profile = getattr(obj, "parent_profile", None)
        return profile.preferred_contact if profile else None

    def get_default_location(self, obj):
        profile = getattr(obj, "parent_profile", None)
        return profile.default_location_id if profile else None


class AccountUpdateSerializer(serializers.ModelSerializer):
    preferred_contact = serializers.ChoiceField(choices=ParentProfile.Contact.choices, required=False)
    default_location = serializers.PrimaryKeyRelatedField(
        queryset=Location.objects.filter(is_active=True),
        required=False,
        allow_null=True,
    )

    class Meta:
        model = User
        fields = ["full_name", "phone", "preferred_contact", "default_location"]

    def update(self, instance, validated_data):
        pref = validated_data.pop("preferred_contact", None)
        has_location = "default_location" in validated_data
        location = validated_data.pop("default_location", None)
        instance = super().update(instance, validated_data)
        if instance.role == "parent":
            profile, _ = ParentProfile.objects.get_or_create(user=instance)
            if pref:
                profile.preferred_contact = pref
            if has_location:
                profile.default_location = location
            profile.save()
        return instance


class _BaseRegisterSerializer(serializers.Serializer):
    email = serializers.EmailField()
    full_name = serializers.CharField(max_length=150)
    password = serializers.CharField(write_only=True, style={"input_type": "password"})
    phone = serializers.CharField(max_length=30, required=False, allow_blank=True)

    def validate_email(self, value):
        value = value.lower().strip()
        if User.objects.filter(email__iexact=value).exists():
            raise serializers.ValidationError("An account with this email already exists.")
        return value

    def validate(self, attrs):
        candidate = User(email=attrs.get("email", ""), full_name=attrs.get("full_name", ""))
        try:
            validate_password(attrs["password"], candidate)
        except DjangoValidationError as exc:
            raise serializers.ValidationError({"password": list(exc.messages)})
        return attrs


class ParentRegisterSerializer(_BaseRegisterSerializer):
    @transaction.atomic
    def create(self, validated_data):
        user = User.objects.create_user(
            email=validated_data["email"],
            password=validated_data["password"],
            full_name=validated_data["full_name"],
            phone=validated_data.get("phone", ""),
            role=User.Role.PARENT,  # role is never taken from client input
        )
        ParentProfile.objects.create(user=user)
        return user


class TutorRegisterSerializer(_BaseRegisterSerializer):
    phone = serializers.CharField(max_length=30)  # required for tutors

    @transaction.atomic
    def create(self, validated_data):
        from tutors.models import TutorProfile

        user = User.objects.create_user(
            email=validated_data["email"],
            password=validated_data["password"],
            full_name=validated_data["full_name"],
            phone=validated_data["phone"],
            role=User.Role.TUTOR,
        )
        TutorProfile.objects.create(user=user, display_name=user.full_name)
        return user


class EmailTokenObtainPairSerializer(TokenObtainPairSerializer):
    def validate(self, attrs):
        attrs[self.username_field] = (attrs.get(self.username_field) or "").strip().lower()
        data = super().validate(attrs)
        data["user"] = UserSerializer(self.user).data
        return data


class ChangePasswordSerializer(serializers.Serializer):
    old_password = serializers.CharField(write_only=True)
    new_password = serializers.CharField(write_only=True)

    def validate_old_password(self, value):
        if not self.context["request"].user.check_password(value):
            raise serializers.ValidationError("Your current password is incorrect.")
        return value

    def validate_new_password(self, value):
        validate_password(value, self.context["request"].user)
        return value


class AdminUserSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ["id", "email", "full_name", "phone", "role", "is_active", "created_at", "last_login"]
        read_only_fields = fields
