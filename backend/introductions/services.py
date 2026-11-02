from django.db import transaction
from django.utils import timezone
from rest_framework.exceptions import ValidationError

from audit.services import log, record_status
from notifications.services import notify
from tutor_requests.models import ParentRequest
from tutor_requests.services import change_status

from .models import Introduction

I = Introduction.Status

NEEDS_CONSENT = {I.MATCH_CONFIRMED, I.COMPLETED}


@transaction.atomic
def change_intro_status(intro, new_status, actor, *, note="", outcome_notes=None, introduced_on=None):
    old = intro.status
    if new_status in NEEDS_CONSENT and not (intro.parent_agreed and intro.tutor_agreed):
        raise ValidationError({"detail": "Both the parent and the tutor must agree before the match can be confirmed."})
    if old in (I.CANCELLED, I.CLOSED) and new_status != old:
        raise ValidationError({"detail": "This introduction is finished. Create a new one if needed."})

    intro.status = new_status
    if outcome_notes is not None:
        intro.outcome_notes = outcome_notes
    if introduced_on is not None:
        intro.introduced_on = introduced_on
    if new_status == I.COMPLETED and not intro.introduced_on:
        intro.introduced_on = timezone.localdate()
    intro.save()

    if new_status != old:
        record_status(intro, old, new_status, actor, note)
        log(actor, "introduction_status_changed", intro, f"{old} -> {new_status}")

    req = intro.parent_request
    if new_status == I.MATCH_CONFIRMED and req.is_open:
        change_status(req, ParentRequest.Status.INTRODUCTION_ARRANGED, actor, latest_update="A tutor match has been confirmed.", note="Match confirmed")
    elif new_status == I.COMPLETED and req.is_open:
        change_status(req, ParentRequest.Status.COMPLETED, actor, latest_update="Your introduction has been completed.", outcome=intro.outcome_notes or None, note="Introduction completed")

    if new_status != old and new_status in (I.MATCH_CONFIRMED, I.COMPLETED):
        notify(req.parent, "Your introduction was arranged", f"Request {req.reference}: open My Introductions.", "/parent/introductions", "introduction")
        notify(intro.tutor.user, "An introduction was arranged for you", "An administrator will be in touch.", "/tutor", "introduction")
    return intro


@transaction.atomic
def record_consent(intro, party, agreed, actor):
    now = timezone.now() if agreed else None
    if party == "parent":
        intro.parent_agreed, intro.parent_agreed_at = agreed, now
    else:
        intro.tutor_agreed, intro.tutor_agreed_at = agreed, now
    if not agreed and intro.contact_shared:
        intro.contact_shared, intro.contact_shared_at = False, None  # withdrawing consent stops sharing
    intro.save()
    log(actor, "introduction_consent_recorded", intro, f"{party}={'agreed' if agreed else 'withdrawn'}")
    return intro


@transaction.atomic
def share_contact(intro, actor):
    if not (intro.parent_agreed and intro.tutor_agreed):
        raise ValidationError({"detail": "Contact details can only be shared after both parties have agreed."})
    if intro.status in (I.CANCELLED, I.CLOSED):
        raise ValidationError({"detail": "This introduction is finished."})
    intro.contact_shared = True
    intro.contact_shared_at = timezone.now()
    intro.save()
    log(actor, "introduction_contact_shared", intro)
    return intro
