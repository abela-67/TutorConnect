import os
import uuid

from django.conf import settings
from django.core.files.storage import FileSystemStorage


class PrivateStorage(FileSystemStorage):
    """Stores credential documents outside MEDIA_ROOT and refuses to produce a URL for them."""

    @property
    def base_location(self):
        return str(settings.PRIVATE_MEDIA_ROOT)

    @property
    def location(self):
        return os.path.abspath(self.base_location)

    def url(self, name):
        raise ValueError("Private documents have no public URL; use the authorised download endpoint.")


def get_private_storage():
    return PrivateStorage()


def document_upload_path(instance, filename):
    ext = os.path.splitext(filename)[1].lower()
    # Random file names: the original name is kept in the database only.
    return f"tutor_{instance.tutor_id}/{uuid.uuid4().hex}{ext}"


def photo_upload_path(instance, filename):
    ext = os.path.splitext(filename)[1].lower()
    return f"tutor_photos/{uuid.uuid4().hex}{ext}"
