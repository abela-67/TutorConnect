from django.conf import settings
from django.db import models


class ParentRequest(models.Model):
    """A parent's need for a tutor. Separate from jobs: a request may never become a public job."""

    class Source(models.TextChoices):
        WEBSITE = "website", "Website"
        TELEPHONE = "telephone", "Telephone"
        INQUIRY = "inquiry", "Converted inquiry"
        OTHER = "other", "Other (walk-in, email...)"

    class Status(models.TextChoices):
        DRAFT = "draft", "Draft (incomplete)"
        NEW = "new", "New"
        IN_REVIEW = "in_review", "In Review"
        MATCHING = "matching", "Finding a Tutor"
        AWAITING_PARENT = "awaiting_parent", "Awaiting Parent"
        JOB_PUBLISHED = "job_published", "Tutor Search Published"
        MATCHED = "matched", "Tutor Matched"
        INTRODUCTION_ARRANGED = "introduction_arranged", "Introduction Arranged"
        COMPLETED = "completed", "Completed"
        CLOSED = "closed", "Closed"
        CANCELLED = "cancelled", "Cancelled"

    class Mode(models.TextChoices):
        ONLINE = "online", "Online"
        IN_PERSON = "in_person", "In person"
        EITHER = "either", "Either"

    CLOSED_STATUSES = ("completed", "closed", "cancelled")

    parent = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL, related_name="requests")
    source = models.CharField(max_length=12, choices=Source.choices, default=Source.WEBSITE, db_index=True)
    status = models.CharField(max_length=24, choices=Status.choices, default=Status.NEW, db_index=True)

    # Only used for requests recorded by an administrator (e.g. by telephone) without a parent account.
    contact_name = models.CharField(max_length=150, blank=True)
    contact_phone = models.CharField(max_length=30, blank=True)
    contact_email = models.EmailField(blank=True)

    subject = models.ForeignKey("catalog.Subject", null=True, blank=True, on_delete=models.PROTECT, related_name="+")
    grade_level = models.ForeignKey("catalog.GradeLevel", null=True, blank=True, on_delete=models.PROTECT, related_name="+")
    location = models.ForeignKey("catalog.Location", null=True, blank=True, on_delete=models.PROTECT, related_name="+")
    teaching_mode = models.CharField(max_length=10, choices=Mode.choices, blank=True)
    preferred_tutor = models.ForeignKey("tutors.TutorProfile", null=True, blank=True, on_delete=models.SET_NULL, related_name="requests_for")
    preferred_gender = models.CharField(max_length=10, blank=True)
    preferred_schedule = models.CharField(max_length=200, blank=True)
    budget_amount = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    additional_requirements = models.TextField(blank=True, max_length=2000)

    # Administrator-only
    internal_notes = models.TextField(blank=True)
    assigned_to = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL, related_name="assigned_requests")
    outcome = models.TextField(blank=True)
    # Shown to the parent
    latest_update = models.CharField(max_length=300, blank=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at"]
        indexes = [models.Index(fields=["status", "-created_at"]), models.Index(fields=["parent", "-created_at"])]

    @property
    def reference(self):
        return f"REQ-{self.pk:05d}"

    @property
    def is_open(self):
        return self.status not in self.CLOSED_STATUSES

    def __str__(self):
        return self.reference
