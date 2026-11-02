from django.conf import settings
from django.db import models


class AuditLog(models.Model):
    """Important administrative actions. Never store passwords, tokens, or unnecessary personal data in `detail`."""

    actor = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL, related_name="audit_logs")
    action = models.CharField(max_length=80, db_index=True)
    entity_type = models.CharField(max_length=50, blank=True)
    entity_id = models.PositiveBigIntegerField(null=True, blank=True)
    detail = models.CharField(max_length=500, blank=True)
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)

    class Meta:
        ordering = ["-created_at", "-id"]
        indexes = [models.Index(fields=["entity_type", "entity_id"])]

    def __str__(self):
        return f"{self.action} ({self.entity_type}#{self.entity_id})"


class StatusHistory(models.Model):
    """Generic history of status changes for tutor applications, requests, jobs, job applications and introductions."""

    entity_type = models.CharField(max_length=50)
    entity_id = models.PositiveBigIntegerField()
    from_status = models.CharField(max_length=50, blank=True)
    to_status = models.CharField(max_length=50)
    changed_by = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL, related_name="+")
    note = models.CharField(max_length=500, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["created_at", "id"]
        indexes = [models.Index(fields=["entity_type", "entity_id"])]
        verbose_name_plural = "status histories"
