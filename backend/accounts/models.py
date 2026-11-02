from django.contrib.auth.models import AbstractUser, BaseUserManager
from django.db import models


class UserManager(BaseUserManager):
    use_in_migrations = True

    def _create_user(self, email, password, **extra):
        if not email:
            raise ValueError("An email address is required.")
        email = self.normalize_email(email).lower()
        user = self.model(email=email, **extra)
        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_user(self, email, password=None, **extra):
        extra.setdefault("is_staff", False)
        extra.setdefault("is_superuser", False)
        extra.setdefault("role", "parent")
        return self._create_user(email, password, **extra)

    def create_superuser(self, email, password=None, **extra):
        """Used by `createsuperuser`. This is the only way an administrator account is created."""
        extra["is_staff"] = True
        extra["is_superuser"] = True
        extra["role"] = "admin"
        return self._create_user(email, password, **extra)


class User(AbstractUser):
    class Role(models.TextChoices):
        PARENT = "parent", "Parent"
        TUTOR = "tutor", "Tutor"
        ADMIN = "admin", "Administrator"

    username = None
    email = models.EmailField(unique=True)
    full_name = models.CharField(max_length=150)
    phone = models.CharField(max_length=30, blank=True)
    role = models.CharField(max_length=10, choices=Role.choices, default=Role.PARENT, db_index=True)
    created_at = models.DateTimeField(auto_now_add=True)

    USERNAME_FIELD = "email"
    REQUIRED_FIELDS = ["full_name"]

    objects = UserManager()

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return self.full_name or self.email

    @property
    def is_admin_role(self):
        return self.role == self.Role.ADMIN


class ParentProfile(models.Model):
    class Contact(models.TextChoices):
        EMAIL = "email", "Email"
        PHONE = "phone", "Phone call"

    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name="parent_profile")
    preferred_contact = models.CharField(max_length=10, choices=Contact.choices, default=Contact.PHONE)
    default_location = models.ForeignKey("catalog.Location", null=True, blank=True, on_delete=models.SET_NULL, related_name="+")

    def __str__(self):
        return f"Parent profile: {self.user}"
