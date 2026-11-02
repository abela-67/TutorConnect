from django.conf import settings
from django.db import models


class Notification(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="notifications")
    kind = models.CharField(max_length=40, default="info")
    title = models.CharField(max_length=200)
    # Keep previews generic: never put contact details, documents or private notes here.
    body = models.CharField(max_length=300, blank=True)
    link = models.CharField(max_length=200, blank=True)  # front-end route the user is authorised to open
    is_read = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at", "-id"]
        indexes = [models.Index(fields=["user", "is_read", "-created_at"])]

    def __str__(self):
        return f"{self.user_id}: {self.title}"
