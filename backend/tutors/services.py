from django.db import transaction
from django.utils import timezone
from rest_framework.exceptions import ValidationError

from audit.services import log, record_status
from notifications.services import notify, notify_admins

from .models import TutorProfile

S = TutorProfile.Status

# action -> (statuses it may be applied from, resulting status)
ACTIONS = {
    "submit": ({S.DRAFT, S.PENDING_SUBMISSION, S.INFO_REQUIRED, S.REJECTED}, S.UNDER_REVIEW),
    "approve": ({S.UNDER_REVIEW, S.INFO_REQUIRED, S.APPROVED}, S.APPROVED),
    "reject": ({S.UNDER_REVIEW, S.INFO_REQUIRED}, S.REJECTED),
    "request_info": ({S.UNDER_REVIEW}, S.INFO_REQUIRED),
    "suspend": ({S.APPROVED, S.UNDER_REVIEW, S.INFO_REQUIRED}, S.SUSPENDED),
    "reinstate": ({S.SUSPENDED}, S.APPROVED),
}
NOTE_REQUIRED = {"reject", "request_info", "suspend"}

# Statuses in which the tutor may edit their profile/credentials.
EDITABLE_STATUSES = {S.DRAFT, S.PENDING_SUBMISSION, S.INFO_REQUIRED, S.REJECTED, S.APPROVED}


def ensure_editable(profile):
    if profile.status not in EDITABLE_STATUSES:
        if profile.status == S.UNDER_REVIEW:
            raise ValidationError({"detail": "Your application is under review and cannot be edited right now."})
        raise ValidationError({"detail": "Your profile cannot be edited while your account is suspended."})


def mark_changed_after_approval(profile, what):
    """Edits to verification-relevant data after approval require renewed review."""
    if profile.status == S.APPROVED and not profile.has_unreviewed_changes:
        profile.has_unreviewed_changes = True
        profile.save(update_fields=["has_unreviewed_changes", "updated_at"])
        notify_admins("Approved tutor changed credentials", f"{profile.display_name} updated {what}; review needed.", "/admin/tutors", "tutor")


def refresh_draft_state(profile):
    """Keep draft/pending_submission in step with how complete the profile is."""
    if profile.status in (S.DRAFT, S.PENDING_SUBMISSION):
        target = S.PENDING_SUBMISSION if not profile.missing_for_submission() else S.DRAFT
        if target != profile.status:
            profile.status = target
            profile.save(update_fields=["status", "updated_at"])


@transaction.atomic
def apply_action(profile, action, actor, note=""):
    allowed_from, target = ACTIONS[action]
    note = (note or "").strip()

    if profile.status not in allowed_from:
        raise ValidationError({"detail": f"This action is not available while the application is '{profile.get_status_display()}'."})
    if action == "approve" and profile.status == S.APPROVED and not profile.has_unreviewed_changes:
        raise ValidationError({"detail": "This profile is already approved and has no changes awaiting review."})
    if action == "submit":
        missing = profile.missing_for_submission()
        if missing:
            raise ValidationError({"detail": "Please complete your profile before submitting.", "missing": missing})
    if action in NOTE_REQUIRED and not note:
        raise ValidationError({"note": "An explanation is required for this decision."})

    old = profile.status
    profile.status = target
    if action in NOTE_REQUIRED:
        profile.status_note = note[:500]
    elif action in ("approve", "reinstate", "submit"):
        profile.status_note = ""
    if action == "submit":
        profile.submitted_at = timezone.now()
    else:
        profile.reviewed_by = actor
        profile.reviewed_at = timezone.now()
    if action in ("approve", "reinstate"):
        profile.has_unreviewed_changes = False
    profile.save()

    record_status(profile, old, target, actor, note)
    log(actor, f"tutor_{action}", profile, f"{old} -> {target}")

    link = "/tutor/profile"
    if action == "submit":
        notify(profile.user, "Application submitted", "Your tutor application is now under review.", link, "tutor")
        notify_admins("New tutor application", f"{profile.display_name} submitted an application.", "/admin/tutors", "tutor")
    elif action == "approve":
        notify(profile.user, "Your tutor profile was approved", "You are now listed and can browse tutoring jobs.", "/tutor/jobs", "tutor")
    elif action == "reject":
        notify(profile.user, "Your application was not approved", "Open your profile to see the reason and next steps.", link, "tutor")
    elif action == "request_info":
        notify(profile.user, "Additional information required", "An administrator needs more information or documents.", link, "tutor")
    elif action == "suspend":
        notify(profile.user, "Your tutor profile was suspended", "Open your profile for details.", link, "tutor")
    elif action == "reinstate":
        notify(profile.user, "Your tutor profile was reinstated", "Your profile is active again.", link, "tutor")
    return profile
