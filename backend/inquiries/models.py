from django.conf import settings
from django.db import models


class PersonalInquiry(models.Model):
    """A private message from a parent to the administrators. Never exposed anywhere public."""

    class Category(models.TextChoices):
        SCHEDULING = "scheduling", "Special scheduling needs"
        TUTOR_QUESTION = "tutor_question", "Question about a tutor"
        NO_TUTOR = "no_tutor", "Help finding a tutor"
        VERIFICATION = "verification", "How verification works"
        COMPLAINT = "complaint", "Complaint or safety concern"
        SERVICES = "services", "Question about our service"
        OTHER = "other", "Other"

    class Status(models.TextChoices):
        NEW = "new", "New"
        IN_PROGRESS = "in_progress", "In Progress"
        AWAITING_PARENT = "awaiting_parent", "Awaiting Parent"
        RESOLVED = "resolved", "Resolved"
        CLOSED = "closed", "Closed"

    class Response(models.TextChoices):
        EMAIL = "email", "Email"
        PHONE = "phone", "Phone call"
        ANY = "any", "Either is fine"

    parent = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="inquiries")
    about_tutor = models.ForeignKey("tutors.TutorProfile", null=True, blank=True, on_delete=models.SET_NULL, related_name="+")
    category = models.CharField(max_length=20, choices=Category.choices, default=Category.OTHER)
    message = models.TextField(max_length=3000)
    preferred_response = models.CharField(max_length=10, choices=Response.choices, default=Response.ANY)
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.NEW, db_index=True)

    assigned_to = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL, related_name="assigned_inquiries")
    internal_notes = models.TextField(blank=True)  # administrators only
    admin_response = models.TextField(blank=True)  # visible to the parent
    converted_request = models.ForeignKey("tutor_requests.ParentRequest", null=True, blank=True, on_delete=models.SET_NULL, related_name="source_inquiries")

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at"]
        indexes = [models.Index(fields=["status", "-created_at"])]
        verbose_name_plural = "personal inquiries"

    @property
    def reference(self):
        return f"INQ-{self.pk:05d}"

    def __str__(self):
        return self.reference
