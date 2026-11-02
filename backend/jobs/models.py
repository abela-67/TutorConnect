from django.conf import settings
from django.db import models


class TutoringJob(models.Model):
    """A public-to-approved-tutors opportunity. Never contains parent identity or contact data."""

    class Status(models.TextChoices):
        DRAFT = "draft", "Draft"
        OPEN = "open", "Open"
        UNDER_REVIEW = "applications_under_review", "Applications Under Review"
        SHORTLISTING = "shortlisting", "Shortlisting"
        TUTOR_SELECTED = "tutor_selected", "Tutor Selected"
        FILLED = "filled", "Filled"
        CLOSED = "closed", "Closed"
        CANCELLED = "cancelled", "Cancelled"

    class Mode(models.TextChoices):
        ONLINE = "online", "Online"
        IN_PERSON = "in_person", "In person"
        EITHER = "either", "Either"

    ACCEPTING = ("open",)  # only Open jobs accept new applications
    TERMINAL = ("filled", "closed", "cancelled")

    title = models.CharField(max_length=150)
    subject = models.ForeignKey("catalog.Subject", null=True, blank=True, on_delete=models.PROTECT, related_name="+")
    grade_level = models.ForeignKey("catalog.GradeLevel", null=True, blank=True, on_delete=models.PROTECT, related_name="+")
    location = models.ForeignKey("catalog.Location", null=True, blank=True, on_delete=models.PROTECT, related_name="+")
    teaching_mode = models.CharField(max_length=10, choices=Mode.choices, blank=True)
    preferred_schedule = models.CharField(max_length=200, blank=True)
    frequency = models.CharField(max_length=100, blank=True)
    duration = models.CharField(max_length=100, blank=True)
    payment_amount = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    payment_note = models.CharField(max_length=150, blank=True)
    required_qualifications = models.TextField(blank=True, max_length=1000)
    additional_requirements = models.TextField(blank=True, max_length=1500)
    application_deadline = models.DateField(null=True, blank=True)

    status = models.CharField(max_length=30, choices=Status.choices, default=Status.DRAFT, db_index=True)
    source_request = models.ForeignKey("tutor_requests.ParentRequest", null=True, blank=True, on_delete=models.SET_NULL, related_name="jobs")
    internal_notes = models.TextField(blank=True)
    outcome = models.TextField(blank=True)
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, on_delete=models.SET_NULL, related_name="+")
    published_at = models.DateTimeField(null=True, blank=True)
    closed_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-published_at", "-created_at"]
        indexes = [
            models.Index(fields=["status", "subject"]),
            models.Index(fields=["status", "location"]),
            models.Index(fields=["status", "grade_level"]),
            models.Index(fields=["status", "teaching_mode"]),
        ]

    @property
    def reference(self):
        return f"JOB-{self.pk:05d}"

    def __str__(self):
        return f"{self.reference} {self.title}"


class JobApplication(models.Model):
    class Status(models.TextChoices):
        SUBMITTED = "submitted", "Submitted"
        UNDER_REVIEW = "under_review", "Under Review"
        SHORTLISTED = "shortlisted", "Shortlisted"
        SELECTED = "selected", "Selected"
        NOT_SELECTED = "not_selected", "Not Selected"
        WITHDRAWN = "withdrawn", "Withdrawn"

    ACTIVE = ("submitted", "under_review", "shortlisted")

    job = models.ForeignKey(TutoringJob, on_delete=models.CASCADE, related_name="applications")
    tutor = models.ForeignKey("tutors.TutorProfile", on_delete=models.CASCADE, related_name="job_applications")
    message = models.CharField(max_length=500, blank=True)
    status = models.CharField(max_length=15, choices=Status.choices, default=Status.SUBMITTED, db_index=True)
    admin_notes = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at"]
        constraints = [models.UniqueConstraint(fields=["job", "tutor"], name="one_application_per_tutor_per_job")]

    def __str__(self):
        return f"{self.tutor} -> {self.job}"
