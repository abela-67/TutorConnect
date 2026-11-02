class NamedFKMixin:
    """Adds human-readable names for foreign keys to serializer output.

    named_fks = (("subject", "subject_name"), ...) -> data["subject_name"] = str(instance.subject) or None
    """

    named_fks = ()

    def to_representation(self, instance):
        data = super().to_representation(instance)
        for attr, key in self.named_fks:
            obj = getattr(instance, attr, None)
            data[key] = str(obj) if obj else None
        return data
