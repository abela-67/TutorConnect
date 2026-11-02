from .models import AuditLog, StatusHistory


def _entity_key(entity):
    return entity.__class__.__name__, entity.pk


def log(actor, action, entity=None, detail=""):
    entity_type, entity_id = _entity_key(entity) if entity is not None else ("", None)
    return AuditLog.objects.create(
        actor=actor if getattr(actor, "is_authenticated", False) else None,
        action=action,
        entity_type=entity_type,
        entity_id=entity_id,
        detail=(detail or "")[:500],
    )


def record_status(entity, from_status, to_status, user=None, note=""):
    entity_type, entity_id = _entity_key(entity)
    return StatusHistory.objects.create(
        entity_type=entity_type,
        entity_id=entity_id,
        from_status=from_status or "",
        to_status=to_status,
        changed_by=user if getattr(user, "is_authenticated", False) else None,
        note=(note or "")[:500],
    )


def history_for(entity):
    entity_type, entity_id = _entity_key(entity)
    return StatusHistory.objects.filter(entity_type=entity_type, entity_id=entity_id).select_related("changed_by")
