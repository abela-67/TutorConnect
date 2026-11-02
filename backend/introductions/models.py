from django.conf import settings
from django.db import models


class Introduction(models.Model):
    """An administrator-facilitated parent-tutor introduction. Contact details are shared only when `contact_shared`."""

    class Status(models.TextChoices):
        PENDING = "pending", "Pending"
        TUTOR_CONTACTED = "tutor_contacted", "Tutor Contacted"
        AWAITING_PARENT = "awaiting_parent", "Awaiting Parent"
        AWAITING_TUTOR = "awaiting_tutor", "Awaiting Tutor"
        MATCH_CONFIRMED = "match_confirmed", "Match Confirmed"
        COMPLETED = "completed", "Introduction Completed"
        CANCELLED = "cancelled", "Cancelled"
        CLOSED = "closed", "Closed"

    parent_request = models.ForeignKey("tutor_requests.ParentRequest", on_delete=models.PROTECT, related_name="introductions")
    tutor = models.ForeignKey("tutors.TutorProfile", on_delete=models.PROTECT, related_name="introductions")
    job = models.ForeignKey("jobs.TutoringJob", null=True, blank=True, on_delete=models.SET_NULL, related_name="introductions")
    responsible_admin = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, on_delete=models.SET_NULL, related_name="introductions")
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.PENDING, db_index=True)

    parent_agreed = models.BooleanField(default=False)
    parent_agreed_at = models.DateTimeField(null=True, blank=True)
    tutor_agreed = models.BooleanField(default=False)
    tutor_agreed_at = models.DateTimeField(null=True, blank=True)
    contact_shared = models.BooleanField(default=False)
    contact_shared_at = models.DateTimeField(null=True, blank=True)

    introduced_on = models.DateField(null=True, blank=True)
    outcome_notes = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at"]
        constraints = [models.UniqueConstraint(fields=["parent_request", "tutor"], name="one_introduction_per_request_and_tutor")]

    def __str__(self):
        return f"Introduction #{self.pk}: {self.parent_request} / {self.tutor}"
