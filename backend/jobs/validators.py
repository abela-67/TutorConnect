import re

from rest_framework import serializers

EMAIL_RE = re.compile(r"[\w.+-]+@[\w-]+\.[\w.-]+")
PHONE_RE = re.compile(r"\+?\d[\d\s\-().]{7,}\d")


def validate_public_text(value):
    """Safety net: job text is visible to every approved tutor, so reject anything that looks like contact details."""
    if not value:
        return value
    if EMAIL_RE.search(value):
        raise serializers.ValidationError("Do not include email addresses in a public job listing.")
    for match in PHONE_RE.finditer(value):
        if len(re.sub(r"\D", "", match.group())) >= 9:
            raise serializers.ValidationError("Do not include phone numbers in a public job listing.")
    return value
