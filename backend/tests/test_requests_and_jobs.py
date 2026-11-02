import json

from audit.models import StatusHistory
from jobs.models import JobApplication, TutoringJob
from notifications.models import Notification
from tutor_requests.models import ParentRequest

from .base import BaseTestCase


class ParentRequestTests(BaseTestCase):
    def setUp(self):
        super().setUp()
        self.parent = self.make_parent()
        self.admin = self.make_admin()
        _, self.tutor = self.make_tutor("t@t.test")

    def payload(self, **extra):
        data = {"subject": self.math.id, "grade_level": self.g10.id, "teaching_mode": "in_person", "location": self.bole.id}
        data.update(extra)
        return data

    def test_minimal_online_request_is_stored_with_parent(self):
        res = self.as_user(self.parent).post("/api/parent/requests/", self.payload(), format="json")
        self.assertEqual(res.status_code, 201)
        req = ParentRequest.objects.get(pk=res.data["id"])
        self.assertEqual(req.parent, self.parent)
        self.assertEqual(req.source, "website")
        self.assertEqual(req.status, "new")
        self.assertTrue(res.data["reference"].startswith("REQ-"))
        self.assertTrue(Notification.objects.filter(user=self.parent, title="Request received").exists())
        self.assertTrue(StatusHistory.objects.filter(entity_type="ParentRequest", entity_id=req.id).exists())

    def test_online_request_needs_no_location(self):
        res = self.as_user(self.parent).post("/api/parent/requests/", self.payload(teaching_mode="online", location=None), format="json")
        self.assertEqual(res.status_code, 201)

    def test_required_fields_are_enforced_but_student_details_are_not_asked_for(self):
        c = self.as_user(self.parent)
        self.assertEqual(c.post("/api/parent/requests/", {"teaching_mode": "online"}, format="json").status_code, 400)
        self.assertEqual(c.post("/api/parent/requests/", self.payload(location=None), format="json").status_code, 400)
        fields = set(self.as_user(self.parent).post("/api/parent/requests/", self.payload(grade_level=self.g5.id), format="json").data)
        for forbidden in ("student_name", "date_of_birth", "school", "address", "internal_notes", "assigned_to"):
            self.assertNotIn(forbidden, fields)

    def test_request_for_specific_tutor_and_unapproved_tutor_rejected(self):
        c = self.as_user(self.parent)
        ok = c.post("/api/parent/requests/", self.payload(preferred_tutor=self.tutor.id), format="json")
        self.assertEqual(ok.status_code, 201)
        _, pending = self.make_tutor("p@t.test", status="under_review")
        bad = c.post("/api/parent/requests/", self.payload(preferred_tutor=pending.id, grade_level=self.g5.id), format="json")
        self.assertEqual(bad.status_code, 400)

    def test_duplicate_submission_is_blocked(self):
        c = self.as_user(self.parent)
        self.assertEqual(c.post("/api/parent/requests/", self.payload(), format="json").status_code, 201)
        self.assertEqual(c.post("/api/parent/requests/", self.payload(), format="json").status_code, 400)

    def test_parent_view_hides_internal_fields(self):
        rid = self.as_user(self.parent).post("/api/parent/requests/", self.payload(), format="json").data["id"]
        req = ParentRequest.objects.get(pk=rid)
        req.internal_notes = "secret staff note"
        req.save()
        body = json.dumps(self.as_user(self.parent).get(f"/api/parent/requests/{rid}/").data)
        self.assertNotIn("secret staff note", body)
        self.assertNotIn("internal_notes", body)

    def test_parent_cannot_set_status_or_edit_via_api(self):
        rid = self.as_user(self.parent).post("/api/parent/requests/", self.payload(), format="json").data["id"]
        c = self.as_user(self.parent)
        self.assertEqual(c.patch(f"/api/parent/requests/{rid}/", {"status": "completed"}, format="json").status_code, 405)

    def test_parent_can_cancel_own_request(self):
        c = self.as_user(self.parent)
        rid = c.post("/api/parent/requests/", self.payload(), format="json").data["id"]
        res = c.post(f"/api/parent/requests/{rid}/cancel/")
        self.assertEqual(res.status_code, 200)
        self.assertEqual(res.data["status"], "cancelled")

    def test_admin_records_telephone_request_without_parent_account(self):
        c = self.as_user(self.admin)
        res = c.post(
            "/api/admin/requests/",
            {"contact_name": "Caller", "contact_phone": "0912345678", "subject": self.math.id, "grade_level": self.g10.id,
             "location": self.bole.id, "teaching_mode": "in_person", "preferred_schedule": "3 days a week"},
            format="json",
        )
        self.assertEqual(res.status_code, 201)
        req = ParentRequest.objects.get(pk=res.data["id"])
        self.assertEqual(req.source, "telephone")
        self.assertIsNone(req.parent)
        self.assertEqual(req.status, "new")
        self.assertEqual(TutoringJob.objects.count(), 0)  # a request does not automatically become a job

    def test_incomplete_phone_request_can_be_saved_as_draft_and_finished_later(self):
        c = self.as_user(self.admin)
        res = c.post("/api/admin/requests/", {"contact_name": "Half a call", "is_draft": True}, format="json")
        self.assertEqual(res.status_code, 201)
        rid = res.data["id"]
        self.assertEqual(res.data["status"], "draft")
        # cannot start processing until the essentials exist
        self.assertEqual(c.post(f"/api/admin/requests/{rid}/set-status/", {"status": "in_review"}, format="json").status_code, 400)
        c.patch(f"/api/admin/requests/{rid}/", {"subject": self.math.id, "grade_level": self.g10.id}, format="json")
        self.assertEqual(c.post(f"/api/admin/requests/{rid}/set-status/", {"status": "in_review"}, format="json").status_code, 200)

    def test_drafts_never_shown_to_parents(self):
        draft = ParentRequest.objects.create(parent=self.parent, status="draft", source="inquiry")
        self.assertEqual(self.results(self.as_user(self.parent).get("/api/parent/requests/")), [])
        self.assertEqual(self.as_user(self.parent).get(f"/api/parent/requests/{draft.id}/").status_code, 404)

    def test_status_change_notifies_parent_and_records_history(self):
        rid = self.as_user(self.parent).post("/api/parent/requests/", self.payload(), format="json").data["id"]
        res = self.as_user(self.admin).post(
            f"/api/admin/requests/{rid}/set-status/", {"status": "matching", "latest_update": "Looking for tutors"}, format="json"
        )
        self.assertEqual(res.status_code, 200)
        self.assertTrue(Notification.objects.filter(user=self.parent, title__startswith="Update on your request").exists())
        parent_view = self.as_user(self.parent).get(f"/api/parent/requests/{rid}/")
        self.assertEqual(parent_view.data["latest_update"], "Looking for tutors")
        self.assertTrue(StatusHistory.objects.filter(entity_type="ParentRequest", entity_id=rid, to_status="matching").exists())

    def test_matching_suggests_only_public_tutors_with_reasons(self):
        self.make_tutor("pend@t.test", status="under_review")
        self.make_tutor("eng@t.test", subjects=[self.english])
        rid = self.as_user(self.parent).post("/api/parent/requests/", self.payload(), format="json").data["id"]
        res = self.as_user(self.admin).get(f"/api/admin/requests/{rid}/matches/")
        self.assertEqual(res.status_code, 200)
        ids = [r["id"] for r in res.data["results"]]
        self.assertEqual(ids, [self.tutor.id])
        self.assertTrue(res.data["results"][0]["reasons"])
        self.assertEqual(self.as_user(self.parent).get(f"/api/admin/requests/{rid}/matches/").status_code, 403)


class JobTests(BaseTestCase):
    def setUp(self):
        super().setUp()
        self.admin = self.make_admin()
        self.parent = self.make_parent("jobparent@t.test", full_name="Private Parent Name", phone="0900555123")
        self.tutor_a_user, self.tutor_a = self.make_tutor("a@t.test")
        self.tutor_b_user, self.tutor_b = self.make_tutor("b@t.test")
        self.phone_request = ParentRequest.objects.create(
            parent=self.parent, source="telephone", status="new", subject=self.math, grade_level=self.g10,
            location=self.bole, teaching_mode="in_person", preferred_schedule="Three days per week",
            additional_requirements="Please call 0900555123, my street is Private Street 5",
            internal_notes="staff-only",
        )

    def job_payload(self, **extra):
        data = {"title": "Grade 10 Mathematics Tutor", "subject": self.math.id, "grade_level": self.g10.id,
                "location": self.bole.id, "teaching_mode": "in_person", "payment_note": "Negotiable"}
        data.update(extra)
        return data

    def publish_job(self, **extra):
        c = self.as_user(self.admin)
        job_id = c.post("/api/admin/jobs/", self.job_payload(**extra), format="json").data["id"]
        res = c.post(f"/api/admin/jobs/{job_id}/publish/")
        self.assertEqual(res.status_code, 200)
        return job_id

    # ---- who may publish
    def test_only_administrators_can_create_or_publish_jobs(self):
        for actor in (self.make_parent("p2@t.test"), self.tutor_a_user):
            self.assertEqual(self.as_user(actor).post("/api/admin/jobs/", self.job_payload(), format="json").status_code, 403)
        res = self.as_user(self.admin).post("/api/admin/jobs/", self.job_payload(), format="json")
        self.assertEqual(res.status_code, 201)
        self.assertEqual(res.data["status"], "draft")

    def test_draft_jobs_are_hidden_and_incomplete_jobs_cannot_be_published(self):
        c = self.as_user(self.admin)
        jid = c.post("/api/admin/jobs/", {"title": "Needs more info"}, format="json").data["id"]
        self.assertEqual(c.post(f"/api/admin/jobs/{jid}/publish/").status_code, 400)
        full = c.post("/api/admin/jobs/", self.job_payload(), format="json").data["id"]
        self.assertEqual(self.results(self.as_user(self.tutor_a_user).get("/api/tutor/jobs/")), [])
        self.assertEqual(self.as_user(self.tutor_a_user).get(f"/api/tutor/jobs/{full}/").status_code, 404)

    # ---- job board access
    def test_job_board_access_rules(self):
        self.publish_job()
        self.assertEqual(self.anonymous().get("/api/tutor/jobs/").status_code, 401)
        self.assertEqual(self.as_user(self.parent).get("/api/tutor/jobs/").status_code, 403)
        pending_user, _ = self.make_tutor("pending@t.test", status="under_review")
        self.assertEqual(self.as_user(pending_user).get("/api/tutor/jobs/").status_code, 403)
        suspended_user, _ = self.make_tutor("susp@t.test", status="suspended")
        self.assertEqual(self.as_user(suspended_user).get("/api/tutor/jobs/").status_code, 403)
        res = self.as_user(self.tutor_a_user).get("/api/tutor/jobs/")
        self.assertEqual(res.status_code, 200)
        self.assertEqual(res.data["count"], 1)

    def test_job_board_filters(self):
        self.publish_job()
        self.publish_job(title="English tutor", subject=self.english.id, grade_level=self.g5.id, location=self.kirkos.id, teaching_mode="online")
        c = self.as_user(self.tutor_a_user)
        self.assertEqual(c.get(f"/api/tutor/jobs/?subject={self.english.id}").data["count"], 1)
        self.assertEqual(c.get(f"/api/tutor/jobs/?location={self.bole.id}&grade_level={self.g10.id}").data["count"], 1)
        self.assertEqual(c.get("/api/tutor/jobs/?teaching_mode=online").data["count"], 1)
        self.assertEqual(c.get("/api/tutor/jobs/?q=English").data["count"], 1)

    # ---- privacy
    def test_job_from_request_keeps_relationship_but_leaks_no_parent_data(self):
        res = self.as_user(self.admin).post(f"/api/admin/requests/{self.phone_request.id}/create-job/")
        self.assertEqual(res.status_code, 201)
        job = TutoringJob.objects.get(pk=res.data["id"])
        self.assertEqual(job.source_request, self.phone_request)
        self.assertEqual(job.status, "draft")
        self.assertEqual(job.subject, self.math)
        self.assertEqual(job.additional_requirements, "")  # free text is never copied automatically
        self.assertEqual(res.data["source_request_reference"], self.phone_request.reference)

        self.as_user(self.admin).post(f"/api/admin/jobs/{job.id}/publish/")
        self.phone_request.refresh_from_db()
        self.assertEqual(self.phone_request.status, "job_published")

        body = json.dumps(self.as_user(self.tutor_a_user).get(f"/api/tutor/jobs/{job.id}/").data)
        listing = json.dumps(self.as_user(self.tutor_a_user).get("/api/tutor/jobs/").data)
        for text in (body, listing):
            for secret in ("Private Parent Name", "0900555123", "jobparent@t.test", "Private Street", "staff-only"):
                self.assertNotIn(secret, text)
            self.assertNotIn("source_request", text)
            self.assertNotIn("internal_notes", text)

    def test_contact_details_are_rejected_in_public_job_text(self):
        c = self.as_user(self.admin)
        res = c.post("/api/admin/jobs/", self.job_payload(additional_requirements="Call 0912345678 after 5pm"), format="json")
        self.assertEqual(res.status_code, 400)
        res = c.post("/api/admin/jobs/", self.job_payload(additional_requirements="Mail parent@example.com"), format="json")
        self.assertEqual(res.status_code, 400)
        ok = c.post("/api/admin/jobs/", self.job_payload(payment_note="3000-4000 birr per month"), format="json")
        self.assertEqual(ok.status_code, 201)

    def test_request_can_be_resolved_without_any_job(self):
        self.assertEqual(self.phone_request.jobs.count(), 0)
        c = self.as_user(self.admin)
        res = c.post("/api/admin/introductions/", {"parent_request": self.phone_request.id, "tutor": self.tutor_a.id}, format="json")
        self.assertEqual(res.status_code, 201)
        self.assertIsNone(res.data["job"])
        self.assertEqual(TutoringJob.objects.count(), 0)

    # ---- applications
    def test_apply_once_and_prevent_duplicates(self):
        jid = self.publish_job()
        c = self.as_user(self.tutor_a_user)
        res = c.post(f"/api/tutor/jobs/{jid}/apply/", {"message": "I am free in the evenings."}, format="json")
        self.assertEqual(res.status_code, 201)
        self.assertEqual(res.data["status"], "submitted")
        self.assertEqual(c.post(f"/api/tutor/jobs/{jid}/apply/", {}, format="json").status_code, 400)
        self.assertEqual(JobApplication.objects.filter(job_id=jid, tutor=self.tutor_a).count(), 1)

    def test_withdraw_then_deliberate_resubmission(self):
        jid = self.publish_job()
        c = self.as_user(self.tutor_a_user)
        app_id = c.post(f"/api/tutor/jobs/{jid}/apply/", {}, format="json").data["id"]
        self.assertEqual(c.post(f"/api/tutor/applications/{app_id}/withdraw/").data["status"], "withdrawn")
        self.assertEqual(c.post(f"/api/tutor/jobs/{jid}/apply/", {}, format="json").status_code, 201)
        self.assertEqual(JobApplication.objects.filter(job_id=jid, tutor=self.tutor_a).count(), 1)

    def test_closed_filled_and_cancelled_jobs_do_not_accept_applications(self):
        c = self.as_user(self.tutor_a_user)
        for status in ("closed", "filled", "cancelled"):
            jid = self.publish_job(title=f"Job {status}")
            self.as_user(self.admin).post(f"/api/admin/jobs/{jid}/set-status/", {"status": status}, format="json")
            res = c.post(f"/api/tutor/jobs/{jid}/apply/", {}, format="json")
            self.assertIn(res.status_code, (400, 404), status)
        self.assertEqual(JobApplication.objects.count(), 0)
        self.assertEqual(self.as_user(self.tutor_a_user).get("/api/tutor/jobs/").data["count"], 0)

    def test_expired_deadline_blocks_applications(self):
        jid = self.publish_job(application_deadline="2000-01-01")
        res = self.as_user(self.tutor_a_user).post(f"/api/tutor/jobs/{jid}/apply/", {}, format="json")
        self.assertEqual(res.status_code, 404)  # also hidden from the list

    def test_applications_are_private_between_tutors(self):
        jid = self.publish_job()
        app_id = self.as_user(self.tutor_a_user).post(f"/api/tutor/jobs/{jid}/apply/", {"message": "mine"}, format="json").data["id"]
        cb = self.as_user(self.tutor_b_user)
        self.assertEqual(self.results(cb.get("/api/tutor/applications/")), [])
        self.assertEqual(cb.get(f"/api/tutor/applications/{app_id}/").status_code, 404)
        self.assertEqual(cb.post(f"/api/tutor/applications/{app_id}/withdraw/").status_code, 404)
        self.assertEqual(cb.get("/api/tutor/jobs/").data["results"][0]["my_application"], None)
        self.assertEqual(self.as_user(self.make_parent("p3@t.test")).get("/api/admin/applications/").status_code, 403)

    # ---- selection workflow
    def test_selection_and_finalization_update_job_applications_and_request(self):
        res = self.as_user(self.admin).post(f"/api/admin/requests/{self.phone_request.id}/create-job/")
        jid = res.data["id"]
        self.as_user(self.admin).post(f"/api/admin/jobs/{jid}/publish/")
        app_a = self.as_user(self.tutor_a_user).post(f"/api/tutor/jobs/{jid}/apply/", {}, format="json").data["id"]
        app_b = self.as_user(self.tutor_b_user).post(f"/api/tutor/jobs/{jid}/apply/", {}, format="json").data["id"]

        admin = self.as_user(self.admin)
        listing = admin.get(f"/api/admin/jobs/{jid}/applications/")
        self.assertEqual(len(listing.data), 2)
        self.assertIn("fit", listing.data[0])

        # applying never means being selected
        self.assertEqual(JobApplication.objects.get(pk=app_a).status, "submitted")
        self.assertEqual(admin.post(f"/api/admin/applications/{app_a}/set-status/", {"status": "shortlisted"}, format="json").status_code, 200)
        self.assertEqual(TutoringJob.objects.get(pk=jid).status, "shortlisting")
        self.assertEqual(admin.post(f"/api/admin/applications/{app_a}/set-status/", {"status": "selected"}, format="json").status_code, 200)
        self.assertEqual(TutoringJob.objects.get(pk=jid).status, "tutor_selected")
        # only one tutor can be selected at a time
        self.assertEqual(admin.post(f"/api/admin/applications/{app_b}/set-status/", {"status": "selected"}, format="json").status_code, 400)

        self.assertEqual(admin.post(f"/api/admin/jobs/{jid}/finalize/", {"outcome": "Selam placed"}, format="json").status_code, 200)
        job = TutoringJob.objects.get(pk=jid)
        self.assertEqual(job.status, "filled")
        self.assertEqual(JobApplication.objects.get(pk=app_a).status, "selected")
        self.assertEqual(JobApplication.objects.get(pk=app_b).status, "not_selected")
        self.phone_request.refresh_from_db()
        self.assertEqual(self.phone_request.status, "matched")
        self.assertTrue(Notification.objects.filter(user=self.tutor_a_user, title__startswith="Application update").exists())

    def test_finalize_requires_selected_tutor(self):
        jid = self.publish_job()
        self.assertEqual(self.as_user(self.admin).post(f"/api/admin/jobs/{jid}/finalize/", {}, format="json").status_code, 400)

    def test_closed_job_can_be_reopened(self):
        jid = self.publish_job()
        c = self.as_user(self.admin)
        c.post(f"/api/admin/jobs/{jid}/set-status/", {"status": "closed"}, format="json")
        self.assertEqual(c.post(f"/api/admin/jobs/{jid}/set-status/", {"status": "open"}, format="json").status_code, 200)
        self.assertEqual(TutoringJob.objects.get(pk=jid).status, "open")
