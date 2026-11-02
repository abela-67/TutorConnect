from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import models

from .storage import document_upload_path, get_private_storage, photo_upload_path


class TutorProfileQuerySet(models.QuerySet):
    def public(self):
        """The ONLY definition of 'publicly visible': approved profile AND active account."""
        return self.filter(status=TutorProfile.Status.APPROVED, user__is_active=True)


class TutorProfile(models.Model):
    class Status(models.TextChoices):
        DRAFT = "draft", "Draft"
        PENDING_SUBMISSION = "pending_submission", "Pending Submission"
        UNDER_REVIEW = "under_review", "Under Review"
        INFO_REQUIRED = "info_required", "Additional Information Required"
        APPROVED = "approved", "Approved"
        REJECTED = "rejected", "Rejected"
        SUSPENDED = "suspended", "Suspended"

    class Gender(models.TextChoices):
        MALE = "male", "Male"
        FEMALE = "female", "Female"
        OTHER = "other", "Other"

    class Mode(models.TextChoices):
        ONLINE = "online", "Online"
        IN_PERSON = "in_person", "In person"
        BOTH = "both", "Both online and in person"

    class RateUnit(models.TextChoices):
        HOUR = "hour", "per hour"
        MONTH = "month", "per month"

    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="tutor_profile")
    display_name = models.CharField(max_length=120)
    photo = models.ImageField(upload_to=photo_upload_path, blank=True)
    bio = models.TextField(blank=True, max_length=3000)
    gender = models.CharField(max_length=10, choices=Gender.choices, blank=True)
    show_gender = models.BooleanField(default=True, help_text="Allow gender to be displayed and used in search.")
    location = models.ForeignKey("catalog.Location", null=True, blank=True, on_delete=models.SET_NULL, related_name="tutors")
    years_experience = models.PositiveSmallIntegerField(default=0)
    teaching_methods = models.TextField(blank=True, max_length=2000)
    teaching_mode = models.CharField(max_length=10, choices=Mode.choices, default=Mode.BOTH)
    languages = models.JSONField(default=list, blank=True)
    rate_amount = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    rate_unit = models.CharField(max_length=10, choices=RateUnit.choices, default=RateUnit.HOUR)
    subjects = models.ManyToManyField("catalog.Subject", blank=True, related_name="tutors")
    grade_levels = models.ManyToManyField("catalog.GradeLevel", blank=True, related_name="tutors")

    status = models.CharField(max_length=20, choices=Status.choices, default=Status.DRAFT)
    status_note = models.CharField(max_length=500, blank=True, help_text="Message shown to the tutor (reason / what is needed).")
    submitted_at = models.DateTimeField(null=True, blank=True)
    reviewed_by = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL, related_name="+")
    reviewed_at = models.DateTimeField(null=True, blank=True)
    has_unreviewed_changes = models.BooleanField(default=False)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    objects = TutorProfileQuerySet.as_manager()

    class Meta:
        ordering = ["-updated_at"]
        indexes = [
            models.Index(fields=["status", "location"]),
            models.Index(fields=["status", "gender"]),
            models.Index(fields=["status", "teaching_mode"]),
            models.Index(fields=["status", "years_experience"]),
        ]

    def __str__(self):
        return self.display_name

    @property
    def is_publicly_listed(self):
        return self.status == self.Status.APPROVED and self.user.is_active

    def missing_for_submission(self):
        missing = []
        if not self.bio.strip():
            missing.append("Professional biography")
        if not self.location_id:
            missing.append("General location")
        if not self.pk or not self.subjects.exists():
            missing.append("At least one subject")
        if not self.pk or not self.grade_levels.exists():
            missing.append("At least one grade level")
        if not self.pk or not self.qualifications.exists():
            missing.append("At least one educational qualification")
        if not self.pk or not self.documents.exists():
            missing.append("At least one supporting document")
        return missing

    COMPLETENESS_ITEMS = 6

    def completeness(self):
        done = self.COMPLETENESS_ITEMS - len(self.missing_for_submission())
        return round(100 * done / self.COMPLETENESS_ITEMS)


class TutorQualification(models.Model):
    class Level(models.TextChoices):
        CERTIFICATE = "certificate", "Certificate"
        DIPLOMA = "diploma", "Diploma"
        BACHELOR = "bachelor", "Bachelor's degree"
        MASTER = "master", "Master's degree"
        DOCTORATE = "doctorate", "Doctorate"
        OTHER = "other", "Other"

    tutor = models.ForeignKey(TutorProfile, on_delete=models.CASCADE, related_name="qualifications")
    level = models.CharField(max_length=20, choices=Level.choices, default=Level.BACHELOR)
    title = models.CharField(max_length=150)
    institution = models.CharField(max_length=150)
    field_of_study = models.CharField(max_length=150, blank=True)
    year = models.PositiveSmallIntegerField(null=True, blank=True)
    # Set only by an administrator after reviewing evidence; reset whenever the tutor edits the entry.
    verified = models.BooleanField(default=False)
    verified_by = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL, related_name="+")
    verified_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ["-year", "id"]

    def __str__(self):
        return f"{self.title} - {self.institution}"


class TutorDocument(models.Model):
    class DocType(models.TextChoices):
        EDUCATION = "education_certificate", "Educational certificate"
        TEACHING = "teaching_qualification", "Teaching qualification"
        PROFESSIONAL = "professional_certificate", "Professional certificate"
        OTHER = "other", "Other document"

    class Status(models.TextChoices):
        PENDING = "pending", "Pending review"
        VERIFIED = "verified", "Verified"
        REJECTED = "rejected", "Rejected"

    tutor = models.ForeignKey(TutorProfile, on_delete=models.CASCADE, related_name="documents")
    qualification = models.ForeignKey(TutorQualification, null=True, blank=True, on_delete=models.SET_NULL, related_name="documents")
    doc_type = models.CharField(max_length=30, choices=DocType.choices, default=DocType.EDUCATION)
    file = models.FileField(upload_to=document_upload_path, storage=get_private_storage)
    original_name = models.CharField(max_length=255)
    content_type = models.CharField(max_length=100, blank=True)
    size = models.PositiveIntegerField(default=0)
    status = models.CharField(max_length=10, choices=Status.choices, default=Status.PENDING)
    reviewer_note = models.CharField(max_length=500, blank=True)
    reviewed_by = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL, related_name="+")
    reviewed_at = models.DateTimeField(null=True, blank=True)
    uploaded_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-uploaded_at"]
        indexes = [models.Index(fields=["status"])]

    def __str__(self):
        return f"{self.original_name} ({self.status})"


class TutorAvailability(models.Model):
    tutor = models.ForeignKey(TutorProfile, on_delete=models.CASCADE, related_name="availability")
    weekday = models.PositiveSmallIntegerField(choices=[(i, str(i)) for i in range(7)])  # 0 = Monday
    start_time = models.TimeField()
    end_time = models.TimeField()

    class Meta:
        ordering = ["weekday", "start_time"]
        indexes = [models.Index(fields=["weekday"])]
        constraints = [models.CheckConstraint(condition=models.Q(end_time__gt=models.F("start_time")), name="availability_end_after_start")]

    def clean(self):
        if self.start_time and self.end_time and self.end_time <= self.start_time:
            raise ValidationError("End time must be after start time.")
