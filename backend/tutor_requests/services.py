from django.db import transaction
from rest_framework.exceptions import ValidationError

from audit.services import log, record_status
from notifications.services import notify

from .models import ParentRequest

S = ParentRequest.Status


@transaction.atomic
def change_status(req, new_status, actor, *, latest_update=None, outcome=None, note=""):
    """Single entry point for request status changes: validates, records history, audits, notifies the parent."""
    old = req.status
    if new_status == old and latest_update is None and outcome is None:
        return req
    if new_status == S.DRAFT and old != S.DRAFT:
        raise ValidationError({"status": "A request cannot go back to draft."})
    if old == S.DRAFT and new_status != S.DRAFT:
        missing = [n for n, v in (("subject", req.subject_id), ("grade level", req.grade_level_id)) if not v]
        if missing:
            raise ValidationError({"detail": f"Add the {' and '.join(missing)} before processing this request."})

    req.status = new_status
    if latest_update is not None:
        req.latest_update = latest_update
    if outcome is not None:
        req.outcome = outcome
    req.save()

    if new_status != old:
        record_status(req, old, new_status, actor, note)
        log(actor, "request_status_changed", req, f"{old} -> {new_status}")
    if req.parent_id and old != S.DRAFT:
        notify(
            req.parent,
            f"Update on your request {req.reference}",
            f"Status: {req.get_status_display()}. Open My Requests for details.",
            "/parent/requests",
            "request",
        )
    return req


def mark_job_published(req, actor):
    if req.status in (S.NEW, S.IN_REVIEW, S.MATCHING, S.AWAITING_PARENT):
        change_status(req, S.JOB_PUBLISHED, actor, note="Job published from this request")
