import json

from audit.models import AuditLog, StatusHistory

from .base import BaseTestCase


class VerificationTests(BaseTestCase):
    def setUp(self):
        super().setUp()
        self.admin = self.make_admin()

    def test_new_applications_remain_private(self):
        for status in ("draft", "pending_submission", "under_review", "info_required", "rejected", "suspended"):
            user, profile = self.make_tutor(f"{status}@t.test", status=status)
            res = self.anonymous().get(f"/api/tutors/{profile.id}/")
            self.assertEqual(res.status_code, 404, status)
        self.assertEqual(self.anonymous().get("/api/tutors/").data["count"], 0)

    def test_submit_requires_complete_profile_then_enters_review(self):
        user, profile = self.make_tutor("sub@t.test", status="draft")
        c = self.as_user(user)
        res = c.post("/api/tutor/profile/submit/")
        self.assertEqual(res.status_code, 400)
        self.assertIn("missing", res.data)
        self.complete_profile(profile)
        res = c.post("/api/tutor/profile/submit/")
        self.assertEqual(res.status_code, 200)
        profile.refresh_from_db()
        self.assertEqual(profile.status, "under_review")
        self.assertEqual(self.anonymous().get("/api/tutors/").data["count"], 0)

    def test_under_review_profile_cannot_be_edited(self):
        user, _ = self.make_tutor("lock@t.test", status="under_review")
        res = self.as_user(user).patch("/api/tutor/profile/", {"bio": "changed"}, format="json")
        self.assertEqual(res.status_code, 400)

    def test_admin_approval_makes_tutor_public_and_is_audited(self):
        user, profile = self.make_tutor("appr@t.test", status="under_review")
        res = self.as_user(self.admin).post(f"/api/admin/tutors/{profile.id}/approve/", {}, format="json")
        self.assertEqual(res.status_code, 200)
        profile.refresh_from_db()
        self.assertEqual(profile.status, "approved")
        self.assertEqual(profile.reviewed_by, self.admin)
        self.assertIsNotNone(profile.reviewed_at)
        self.assertEqual(self.anonymous().get("/api/tutors/").data["count"], 1)
        self.assertTrue(AuditLog.objects.filter(action="tutor_approve", entity_id=profile.id).exists())
        self.assertTrue(StatusHistory.objects.filter(entity_type="TutorProfile", entity_id=profile.id, to_status="approved").exists())

    def test_only_administrators_can_approve(self):
        user, profile = self.make_tutor("self@t.test", status="under_review")
        for actor in (user, self.make_parent()):
            res = self.as_user(actor).post(f"/api/admin/tutors/{profile.id}/approve/", {}, format="json")
            self.assertEqual(res.status_code, 403)
        profile.refresh_from_db()
        self.assertEqual(profile.status, "under_review")

    def test_rejection_requires_reason_and_removes_from_directory(self):
        user, profile = self.make_tutor("rej@t.test", status="under_review")
        c = self.as_user(self.admin)
        self.assertEqual(c.post(f"/api/admin/tutors/{profile.id}/reject/", {}, format="json").status_code, 400)
        res = c.post(f"/api/admin/tutors/{profile.id}/reject/", {"note": "Certificate unreadable"}, format="json")
        self.assertEqual(res.status_code, 200)
        profile.refresh_from_db()
        self.assertEqual(profile.status, "rejected")
        self.assertEqual(profile.status_note, "Certificate unreadable")
        self.assertEqual(self.anonymous().get("/api/tutors/").data["count"], 0)

    def test_rejected_tutor_can_correct_and_resubmit(self):
        user, profile = self.make_tutor("redo@t.test", status="rejected")
        self.complete_profile(profile)
        res = self.as_user(user).post("/api/tutor/profile/submit/")
        self.assertEqual(res.status_code, 200)
        profile.refresh_from_db()
        self.assertEqual(profile.status, "under_review")

    def test_suspended_or_deactivated_tutors_disappear_from_directory(self):
        user, profile = self.make_tutor("vis@t.test")
        self.assertEqual(self.anonymous().get("/api/tutors/").data["count"], 1)
        user.is_active = False
        user.save()
        self.assertEqual(self.anonymous().get("/api/tutors/").data["count"], 0)
        user.is_active = True
        user.save()
        self.as_user(self.admin).post(f"/api/admin/tutors/{profile.id}/suspend/", {"note": "Complaint under investigation"}, format="json")
        self.assertEqual(self.anonymous().get("/api/tutors/").data["count"], 0)

    def test_changes_after_approval_are_flagged_for_review(self):
        user, profile = self.make_tutor("chg@t.test")
        res = self.as_user(user).post(
            "/api/tutor/qualifications/", {"level": "master", "title": "MSc", "institution": "Uni", "year": 2020}, format="json"
        )
        self.assertEqual(res.status_code, 201)
        self.assertFalse(res.data["verified"])
        profile.refresh_from_db()
        self.assertTrue(profile.has_unreviewed_changes)
        detail = self.anonymous().get(f"/api/tutors/{profile.id}/")
        self.assertEqual(detail.data["verification"]["verified_qualifications"], 0)
        self.assertTrue(detail.data["verification"]["has_changes_awaiting_review"])

    def test_only_reviewed_qualifications_are_shown_as_verified(self):
        user, profile = self.make_tutor("ver@t.test")
        doc = self.complete_profile(profile)
        qual = profile.qualifications.first()
        doc.qualification = qual
        doc.save()
        self.assertEqual(self.anonymous().get(f"/api/tutors/{profile.id}/").data["verified_qualifications"], 0)
        res = self.as_user(self.admin).post(f"/api/admin/documents/{doc.id}/review/", {"status": "verified"}, format="json")
        self.assertEqual(res.status_code, 200)
        self.assertEqual(self.anonymous().get(f"/api/tutors/{profile.id}/").data["verified_qualifications"], 1)


class DirectoryTests(BaseTestCase):
    def setUp(self):
        super().setUp()
        _, self.selam = self.make_tutor("selam@t.test", display_name="Selam", gender="female", subjects=[self.math], grades=[self.g10], teaching_mode="in_person", years_experience=6)
        _, self.dawit = self.make_tutor("dawit@t.test", display_name="Dawit", gender="male", location=self.kirkos, subjects=[self.english], grades=[self.g5], teaching_mode="online", years_experience=2)
        _, self.hidden = self.make_tutor("hidden@t.test", display_name="Hidden", gender="female", subjects=[self.math], grades=[self.g10], show_gender=False)
        self.make_tutor("pending@t.test", status="under_review", display_name="Pending", gender="female", subjects=[self.math], grades=[self.g10])

    def names(self, params=""):
        res = self.anonymous().get(f"/api/tutors/?{params}")
        self.assertEqual(res.status_code, 200)
        return sorted(t["display_name"] for t in res.data["results"])

    def test_directory_lists_only_approved_active_tutors(self):
        self.assertEqual(self.names(), ["Dawit", "Hidden", "Selam"])

    def test_gender_location_and_subject_filters(self):
        self.assertEqual(self.names("gender=male"), ["Dawit"])
        self.assertEqual(self.names(f"location={self.kirkos.id}"), ["Dawit"])
        self.assertEqual(self.names(f"subject={self.english.id}"), ["Dawit"])

    def test_filters_combine_with_and(self):
        q = f"gender=female&location={self.bole.id}&subject={self.math.id}&grade_level={self.g10.id}&teaching_mode=in_person"
        self.assertEqual(self.names(q), ["Selam"])  # Hidden excluded: gender not shown

    def test_gender_filter_respects_show_gender_flag(self):
        self.assertNotIn("Hidden", self.names("gender=female"))
        detail = self.anonymous().get(f"/api/tutors/{self.hidden.id}/")
        self.assertIsNone(detail.data["gender"])

    def test_teaching_mode_filter_includes_both(self):
        self.profile_both = self.make_tutor("both@t.test", display_name="Both", teaching_mode="both")[1]
        self.assertIn("Both", self.names("teaching_mode=online"))
        self.assertNotIn("Selam", self.names("teaching_mode=online"))

    def test_experience_filter(self):
        self.assertEqual(self.names("min_experience=5"), ["Selam"])

    def test_empty_result_is_graceful(self):
        res = self.anonymous().get(f"/api/tutors/?subject={self.english.id}&gender=female")
        self.assertEqual(res.status_code, 200)
        self.assertEqual(res.data["count"], 0)
        self.assertEqual(res.data["results"], [])

    def test_invalid_filter_value_is_rejected(self):
        self.assertEqual(self.anonymous().get("/api/tutors/?gender=banana").status_code, 400)
        self.assertEqual(self.anonymous().get("/api/tutors/?subject=abc").status_code, 400)

    def test_results_are_paginated(self):
        res = self.anonymous().get("/api/tutors/?page_size=2")
        self.assertEqual(len(res.data["results"]), 2)
        self.assertEqual(res.data["count"], 3)
        self.assertIsNotNone(res.data["next"])

    def test_public_profile_never_exposes_private_data(self):
        user, profile = self.make_tutor("priv@t.test", display_name="Private Pat")
        self.complete_profile(profile)
        for url in ("/api/tutors/", f"/api/tutors/{profile.id}/"):
            body = json.dumps(self.anonymous().get(url).data)
            self.assertNotIn("priv@t.test", body)
            self.assertNotIn("0911000001", body)
            self.assertNotIn("cert.pdf", body)
            self.assertNotIn("documents", body)
            self.assertNotIn("status_note", body)

    def test_featured_endpoint_only_returns_public_tutors(self):
        res = self.anonymous().get("/api/tutors/featured/")
        self.assertEqual(res.status_code, 200)
        self.assertNotIn("Pending", [t["display_name"] for t in res.data])
