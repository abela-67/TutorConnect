import shutil
import tempfile

from django.core.cache import cache
from django.core.files.base import ContentFile
from django.test import override_settings
from rest_framework.test import APITestCase

from accounts.models import ParentProfile, User
from catalog.models import GradeLevel, Location, Subject
from tutors.models import TutorDocument, TutorProfile, TutorQualification

PW = "Sturdy-Pass-7391!"


class BaseTestCase(APITestCase):
    """Shared fixtures. Uploaded files go to a temporary directory that is removed afterwards."""

    @classmethod
    def setUpClass(cls):
        cls._tmp = tempfile.mkdtemp()
        cls._override = override_settings(PRIVATE_MEDIA_ROOT=cls._tmp, MEDIA_ROOT=cls._tmp)
        cls._override.enable()
        super().setUpClass()

    @classmethod
    def tearDownClass(cls):
        super().tearDownClass()
        cls._override.disable()
        shutil.rmtree(cls._tmp, ignore_errors=True)

    def setUp(self):
        cache.clear()  # reset throttling counters between tests
        self.bole = Location.objects.create(country="Ethiopia", city="Addis Ababa", area="Bole")
        self.kirkos = Location.objects.create(country="Ethiopia", city="Addis Ababa", area="Kirkos")
        self.math = Subject.objects.create(name="Mathematics")
        self.english = Subject.objects.create(name="English")
        self.g10 = GradeLevel.objects.create(name="Grade 10", order=10)
        self.g5 = GradeLevel.objects.create(name="Grade 5", order=5)

    # ---- factories
    def make_user(self, email, role, **kw):
        return User.objects.create_user(
            email=email, password=PW, role=role, full_name=kw.pop("full_name", email.split("@")[0]), **kw
        )

    def make_admin(self, email="admin@t.test"):
        return User.objects.create_superuser(email=email, password=PW, full_name="Admin User")

    def make_parent(self, email="parent@t.test", **kw):
        user = self.make_user(email, "parent", phone=kw.pop("phone", "0900000001"), **kw)
        ParentProfile.objects.create(user=user)
        return user

    def make_tutor(self, email="tutor@t.test", status="approved", subjects=None, grades=None, **kw):
        user = self.make_user(email, "tutor", phone="0911000001")
        profile = TutorProfile.objects.create(
            user=user,
            display_name=kw.pop("display_name", user.full_name),
            status=status,
            location=kw.pop("location", self.bole),
            bio=kw.pop("bio", "An experienced tutor."),
            **kw,
        )
        profile.subjects.set(subjects if subjects is not None else [self.math])
        profile.grade_levels.set(grades if grades is not None else [self.g10])
        return user, profile

    def complete_profile(self, profile):
        TutorQualification.objects.create(tutor=profile, title="BSc", institution="Uni", year=2015)
        doc = TutorDocument(tutor=profile, doc_type="education_certificate", original_name="cert.pdf", size=10)
        doc.file.save("cert.pdf", ContentFile(b"%PDF-1.4 test"), save=True)
        return doc

    def as_user(self, user):
        self.client.force_authenticate(user)
        return self.client

    def anonymous(self):
        self.client.force_authenticate(None)
        return self.client

    def results(self, response):
        return response.data["results"] if isinstance(response.data, dict) and "results" in response.data else response.data
