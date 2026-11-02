from django.db import transaction
from django.utils import timezone
from rest_framework.exceptions import ValidationError

from audit.services import log, record_status
from notifications.services import notify

from .models import JobApplication, TutoringJob

J = TutoringJob.Status
A = JobApplication.Status


def is_accepting(job):
    """Only 'Open' jobs whose deadline (if any) has not passed accept applications."""
    if job.status not in TutoringJob.ACCEPTING:
        return False
    if job.application_deadline and job.application_deadline < timezone.localdate():
        return False
    return True


def create_job_from_request(req, actor):
    """Prefill a DRAFT job from a request. Only structured, non-identifying fields are copied.

    Free text (additional requirements, notes, contact info) is NOT copied because it may contain private details.
    """
    parts = [p for p in (req.grade_level.name if req.grade_level_id else "", req.subject.name if req.subject_id else "") if p]
    title = " ".join(parts) + " Tutor" if parts else "Tutor needed"
    job = TutoringJob.objects.create(
        title=title,
        subject=req.subject,
        grade_level=req.grade_level,
        location=req.location,
        teaching_mode=req.teaching_mode,
        preferred_schedule=req.preferred_schedule,
        payment_amount=req.budget_amount,
        source_request=req,
        created_by=actor,
    )
    record_status(job, "", J.DRAFT, actor, f"Created from {req.reference}")
    log(actor, "job_created_from_request", job, f"request={req.pk}")
    return job


def validate_publishable(job):
    problems = []
    if not job.title.strip():
        problems.append("title")
    if not job.subject_id:
        problems.append("subject")
    if not job.grade_level_id:
        problems.append("grade level")
    if not job.teaching_mode:
        problems.append("teaching mode")
    if job.teaching_mode != "online" and not job.location_id:
        problems.append("location")
    if problems:
        raise ValidationError({"detail": f"Complete these fields before publishing: {', '.join(problems)}."})


@transaction.atomic
def change_job_status(job, new_status, actor, note=""):
    old = job.status
    if new_status == old:
        return job
    if new_status == J.DRAFT:
        raise ValidationError({"status": "A job cannot return to draft."})
    if new_status == J.OPEN:
        validate_publishable(job)
        if not job.published_at:
            job.published_at = timezone.now()
        job.closed_at = None
    if new_status in (J.FILLED, J.CLOSED, J.CANCELLED):
        job.closed_at = timezone.now()
    job.status = new_status
    job.save()
    record_status(job, old, new_status, actor, note)
    log(actor, "job_published" if (new_status == J.OPEN and old == J.DRAFT) else "job_status_changed", job, f"{old} -> {new_status}")

    if new_status == J.OPEN and old == J.DRAFT and job.source_request_id:
        from tutor_requests.services import mark_job_published

        mark_job_published(job.source_request, actor)

    if new_status in (J.CLOSED, J.CANCELLED):
        for app in job.applications.filter(status__in=JobApplication.ACTIVE).select_related("tutor__user"):
            notify(app.tutor.user, f"A job you applied for was {'cancelled' if new_status == J.CANCELLED else 'closed'}", job.title, "/tutor/applications", "job")
    return job


@transaction.atomic
def change_application_status(app, new_status, actor, note=""):
    if app.status == A.WITHDRAWN:
        raise ValidationError({"detail": "This application was withdrawn by the tutor."})
    if new_status not in (A.UNDER_REVIEW, A.SHORTLISTED, A.SELECTED, A.NOT_SELECTED):
        raise ValidationError({"status": "Invalid status."})
    job = app.job
    if new_status == A.SELECTED:
        if job.status in (J.DRAFT, J.CANCELLED, J.CLOSED, J.FILLED):
            raise ValidationError({"detail": "A tutor cannot be selected for a job that is not open."})
        if job.applications.filter(status=A.SELECTED).exclude(pk=app.pk).exists():
            raise ValidationError({"detail": "Another tutor is already selected. Change that application first."})
    old = app.status
    if old == new_status:
        return app
    app.status = new_status
    app.save()
    record_status(app, old, new_status, actor, note)
    log(actor, "application_status_changed", app, f"{old} -> {new_status}")

    if new_status == A.SELECTED and job.status in (J.OPEN, J.UNDER_REVIEW, J.SHORTLISTING):
        change_job_status(job, J.TUTOR_SELECTED, actor, "Tutor selected")
    elif new_status == A.SHORTLISTED and job.status in (J.OPEN, J.UNDER_REVIEW):
        change_job_status(job, J.SHORTLISTING, actor, "Shortlisting started")
    elif new_status == A.UNDER_REVIEW and job.status == J.OPEN:
        change_job_status(job, J.UNDER_REVIEW, actor, "Review started")

    messages = {
        A.UNDER_REVIEW: "Your application is being reviewed.",
        A.SHORTLISTED: "You were shortlisted.",
        A.SELECTED: "You were selected. An administrator will contact you about next steps.",
        A.NOT_SELECTED: "You were not selected this time.",
    }
    notify(app.tutor.user, f"Application update: {job.title}", messages[new_status], "/tutor/applications", "job")
    return app


@transaction.atomic
def finalize_job(job, actor, outcome=""):
    """Mark the job filled once a tutor is selected; remaining active applicants become 'not selected'."""
    selected = job.applications.filter(status=A.SELECTED).select_related("tutor__user").first()
    if not selected:
        raise ValidationError({"detail": "Select a tutor before finalizing the job."})
    others = job.applications.filter(status__in=JobApplication.ACTIVE).select_related("tutor__user")
    for app in others:
        change_application_status(app, A.NOT_SELECTED, actor, "Job filled")
    job.outcome = outcome
    job.save(update_fields=["outcome", "updated_at"])
    change_job_status(job, J.FILLED, actor, outcome[:500] if outcome else "Job filled")
    if job.source_request_id:
        from tutor_requests.models import ParentRequest
        from tutor_requests.services import change_status

        req = job.source_request
        if req.status in (ParentRequest.Status.JOB_PUBLISHED, ParentRequest.Status.MATCHING, ParentRequest.Status.IN_REVIEW, ParentRequest.Status.NEW, ParentRequest.Status.AWAITING_PARENT):
            change_status(req, ParentRequest.Status.MATCHED, actor, latest_update="A tutor has been found for you.", note="Job filled")
    return job
