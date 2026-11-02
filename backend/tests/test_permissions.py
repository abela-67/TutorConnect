from django.core.files.uploadedfile import SimpleUploadedFile

from accounts.models import User

from .base import PW, BaseTestCase


class RolePermissionTests(BaseTestCase):
    def test_parent_cannot_access_tutor_only_pages(self):
        parent = self.make_parent()
        c = self.as_user(parent)
        self.assertEqual(c.get("/api/tutor/profile/").status_code, 403)
        self.assertEqual(c.get("/api/tutor/jobs/").status_code, 403)
        self.assertEqual(c.get("/api/tutor/applications/").status_code, 403)

    def test_tutor_cannot_access_administrator_pages(self):
        tutor, _ = self.make_tutor()
        c = self.as_user(tutor)
        for url in ("/api/admin/stats/", "/api/admin/tutors/", "/api/admin/requests/", "/api/admin/jobs/",
                    "/api/admin/introductions/", "/api/admin/inquiries/", "/api/admin/audit-logs/", "/api/admin/users/"):
            self.assertEqual(c.get(url).status_code, 403, url)

    def test_parent_cannot_access_administrator_pages(self):
        c = self.as_user(self.make_parent())
        self.assertEqual(c.get("/api/admin/requests/").status_code, 403)
        self.assertEqual(c.post("/api/admin/jobs/", {"title": "x"}, format="json").status_code, 403)

    def test_unauthenticated_cannot_submit_requests_or_inquiries(self):
        c = self.anonymous()
        payload = {"subject": self.math.id, "grade_level": self.g10.id, "teaching_mode": "online"}
        self.assertEqual(c.post("/api/parent/requests/", payload, format="json").status_code, 401)
        self.assertEqual(c.post("/api/parent/inquiries/", {"message": "Hello there"}, format="json").status_code, 401)

    def test_parent_cannot_view_another_parents_request(self):
        owner, other = self.make_parent("a@t.test"), self.make_parent("b@t.test")
        payload = {"subject": self.math.id, "grade_level": self.g10.id, "teaching_mode": "online"}
        created = self.as_user(owner).post("/api/parent/requests/", payload, format="json")
        self.assertEqual(created.status_code, 201)
        rid = created.data["id"]
        c = self.as_user(other)
        self.assertEqual(c.get(f"/api/parent/requests/{rid}/").status_code, 404)
        self.assertEqual(self.results(c.get("/api/parent/requests/")), [])
        self.assertEqual(c.post(f"/api/parent/requests/{rid}/cancel/").status_code, 404)

    def test_registration_ignores_requested_role(self):
        res = self.anonymous().post(
            "/api/auth/register/parent/",
            {"email": "sneaky@t.test", "full_name": "Sneaky", "password": PW, "role": "admin", "is_staff": True},
            format="json",
        )
        self.assertEqual(res.status_code, 201)
        user = User.objects.get(email="sneaky@t.test")
        self.assertEqual(user.role, "parent")
        self.assertFalse(user.is_staff)

    def test_tutor_registration_creates_private_draft_profile(self):
        res = self.anonymous().post(
            "/api/auth/register/tutor/",
            {"email": "newtutor@t.test", "full_name": "New Tutor", "password": PW, "phone": "0911222333"},
            format="json",
        )
        self.assertEqual(res.status_code, 201)
        user = User.objects.get(email="newtutor@t.test")
        self.assertEqual(user.role, "tutor")
        self.assertEqual(user.tutor_profile.status, "draft")

    def test_login_returns_tokens_and_role(self):
        self.make_parent("login@t.test")
        res = self.anonymous().post("/api/auth/token/", {"email": "LOGIN@t.test", "password": PW}, format="json")
        self.assertEqual(res.status_code, 200)
        self.assertIn("access", res.data)
        self.assertEqual(res.data["user"]["role"], "parent")

    def test_suspended_account_cannot_log_in(self):
        user = self.make_parent("gone@t.test")
        user.is_active = False
        user.save()
        res = self.anonymous().post("/api/auth/token/", {"email": "gone@t.test", "password": PW}, format="json")
        self.assertEqual(res.status_code, 401)

    def test_admin_cannot_be_suspended_through_api(self):
        admin, other_admin = self.make_admin("a1@t.test"), self.make_admin("a2@t.test")
        res = self.as_user(admin).post(f"/api/admin/users/{other_admin.id}/suspend/")
        self.assertEqual(res.status_code, 403)


class DocumentAccessTests(BaseTestCase):
    def setUp(self):
        super().setUp()
        self.owner, self.profile = self.make_tutor("owner@t.test", status="under_review")
        self.doc = self.complete_profile(self.profile)
        self.url = f"/api/documents/{self.doc.id}/download/"

    def test_unauthenticated_cannot_download(self):
        self.assertEqual(self.anonymous().get(self.url).status_code, 401)

    def test_other_tutor_and_parent_cannot_download(self):
        other, _ = self.make_tutor("other@t.test")
        self.assertEqual(self.as_user(other).get(self.url).status_code, 404)
        self.assertEqual(self.as_user(self.make_parent()).get(self.url).status_code, 404)

    def test_owner_and_admin_can_download_and_response_is_not_cacheable(self):
        res = self.as_user(self.owner).get(self.url)
        self.assertEqual(res.status_code, 200)
        self.assertIn("no-store", res["Cache-Control"])
        res.close()
        res = self.as_user(self.make_admin()).get(self.url)
        self.assertEqual(res.status_code, 200)
        res.close()

    def test_document_has_no_public_url(self):
        with self.assertRaises(ValueError):
            self.doc.file.url

    def test_upload_validation(self):
        c = self.as_user(self.owner)
        bad_ext = SimpleUploadedFile("notes.txt", b"hello", content_type="text/plain")
        self.assertEqual(c.post("/api/tutor/documents/", {"file": bad_ext, "doc_type": "other"}, format="multipart").status_code, 400)
        fake_pdf = SimpleUploadedFile("fake.pdf", b"not really a pdf", content_type="application/pdf")
        self.assertEqual(c.post("/api/tutor/documents/", {"file": fake_pdf, "doc_type": "other"}, format="multipart").status_code, 400)
        good = SimpleUploadedFile("good.pdf", b"%PDF-1.4 hello", content_type="application/pdf")
        # under_review profiles are locked; move to a draft so the upload is allowed
        self.profile.status = "draft"
        self.profile.save()
        res = c.post("/api/tutor/documents/", {"file": good, "doc_type": "other"}, format="multipart")
        self.assertEqual(res.status_code, 201)
        self.assertNotIn("file", res.data)  # no file path/URL leaks back to the client
