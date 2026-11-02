import logging

from django.conf import settings
from django.core.mail import send_mail

from .models import Notification

logger = logging.getLogger(__name__)


def _maybe_email(user, title, body):
    if not getattr(settings, "EMAIL_NOTIFICATIONS_ENABLED", False) or not user.email:
        return
    try:
        send_mail(title, body or title, None, [user.email], fail_silently=True)
    except Exception:  # email must never break a workflow
        logger.exception("Could not send notification email")


def notify(user, title, body="", link="", kind="info"):
    """Create an in-app notification (and optionally an email). `user` may be None (e.g. phone requests)."""
    if user is None:
        return None
    notification = Notification.objects.create(user=user, title=title[:200], body=body[:300], link=link[:200], kind=kind)
    _maybe_email(user, title, body)
    return notification


def notify_admins(title, body="", link="", kind="admin"):
    from accounts.models import User

    admins = list(User.objects.filter(role=User.Role.ADMIN, is_active=True))
    Notification.objects.bulk_create(
        [Notification(user=a, title=title[:200], body=body[:300], link=link[:200], kind=kind) for a in admins]
    )
