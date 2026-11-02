import json

from audit.models import StatusHistory
from inquiries.models import PersonalInquiry
from introductions.models import Introduction
from tutor_requests.models import ParentRequest

from .base import BaseTestCase


class IntroductionTests(BaseTestCase):
    def setUp(self):
        super().setUp()
        self.admin = self.make_admin()
        self.parent = self.make_parent()
        self.tutor_user, self.tutor = self.make_tutor("intro@t.test")
        self.req = ParentRequest.objects.create(
            parent=self.parent, source="website", status="matching", subject=self.math, grade_level=self.g10,
            location=self.bole, teaching_mode="in_person",
        )

    def create(self, **extra):
        data = {"parent_request": self.req.id, "tutor": self.tutor.id}
        data.update(extra)
        return self.as_user(self.admin).post("/api/admin/introductions/", data, format="json")

    def test_only_administrators_can_create_or_change_introductions(self):
        for actor in (self.parent, self.tutor_user):
            c = self.as_user(actor)
            self.assertEqual(c.post("/api/admin/introductions/", {"parent_request": self.req.id, "tutor": self.tutor.id}, format="json").status_code, 403)
        intro_id = self.create().data["id"]
        for actor in (self.parent, self.tutor_user):
            c = self.as_user(actor)
            self.assertEqual(c.patch(f"/api/admin/introductions/{intro_id}/", {"outcome_notes": "x"}, format="json").status_code, 403)
            self.assertEqual(c.post(f"/api/admin/introductions/{intro_id}/set-status/", {"status": "closed"}, format="json").status_code, 403)

    def test_records_are_linked_and_creation_is_recorded(self):
        res = self.create()
        self.assertEqual(res.status_code, 201)
        intro = Introduction.objects.get(pk=res.data["id"])
        self.assertEqual((intro.parent_request, intro.tutor, intro.responsible_admin), (self.req, self.tutor, self.admin))
        self.assertEqual(intro.status, "pending")
        self.assertTrue(StatusHistory.objects.filter(entity_type="Introduction", entity_id=intro.id).exists())

    def test_cannot_introduce_unapproved_tutor_or_duplicate(self):
        _, pending = self.make_tutor("pend@t.test", status="under_review")
        self.assertEqual(self.create(tutor=pending.id).status_code, 400)
        self.assertEqual(self.create().status_code, 201)
        self.assertEqual(self.create().status_code, 400)

    def test_status_changes_are_recorded_and_need_consent_to_confirm(self):
        intro_id = self.create().data["id"]
        c = self.as_user(self.admin)
        self.assertEqual(c.post(f"/api/admin/introductions/{intro_id}/set-status/", {"status": "tutor_contacted"}, format="json").status_code, 200)
        # cannot confirm until both parties agreed
        self.assertEqual(c.post(f"/api/admin/introductions/{intro_id}/set-status/", {"status": "match_confirmed"}, format="json").status_code, 400)
        c.post(f"/api/admin/introductions/{intro_id}/consent/", {"party": "parent", "agreed": True}, format="json")
        c.post(f"/api/admin/introductions/{intro_id}/consent/", {"party": "tutor", "agreed": True}, format="json")
        self.assertEqual(c.post(f"/api/admin/introductions/{intro_id}/set-status/", {"status": "match_confirmed"}, format="json").status_code, 200)
        self.req.refresh_from_db()
        self.assertEqual(self.req.status, "introduction_arranged")
        self.assertEqual(StatusHistory.objects.filter(entity_type="Introduction", entity_id=intro_id).count(), 3)  # created + 2 changes

        res = c.post(f"/api/admin/introductions/{intro_id}/set-status/", {"status": "completed", "outcome_notes": "Lessons started"}, format="json")
        self.assertEqual(res.status_code, 200)
        self.req.refresh_from_db()
        self.assertEqual(self.req.status, "completed")
        self.assertEqual(Introduction.objects.get(pk=intro_id).outcome_notes, "Lessons started")

    def test_contact_details_are_shared_only_after_consent(self):
        intro_id = self.create().data["id"]
        admin = self.as_user(self.admin)
        parent = self.as_user(self.parent)

        view = parent.get(f"/api/parent/introductions/{intro_id}/")
        self.assertEqual(view.status_code, 200)
        self.assertIsNone(view.data["tutor_contact"])
        self.assertNotIn("0911000001", json.dumps(view.data))
        self.assertNotIn("intro@t.test", json.dumps(view.data))

        self.assertEqual(admin.post(f"/api/admin/introductions/{intro_id}/share-contact/").status_code, 400)
        admin.post(f"/api/admin/introductions/{intro_id}/consent/", {"party": "parent", "agreed": True}, format="json")
        self.assertEqual(admin.post(f"/api/admin/introductions/{intro_id}/share-contact/").status_code, 400)
        admin.post(f"/api/admin/introductions/{intro_id}/consent/", {"party": "tutor", "agreed": True}, format="json")
        self.assertEqual(admin.post(f"/api/admin/introductions/{intro_id}/share-contact/").status_code, 200)

        shared = parent.get(f"/api/parent/introductions/{intro_id}/")
        self.assertEqual(shared.data["tutor_contact"]["phone"], "0911000001")

        # withdrawing consent revokes sharing
        admin.post(f"/api/admin/introductions/{intro_id}/consent/", {"party": "tutor", "agreed": False}, format="json")
        self.assertIsNone(parent.get(f"/api/parent/introductions/{intro_id}/").data["tutor_contact"])

    def test_parent_sees_only_their_own_introductions(self):
        intro_id = self.create().data["id"]
        other = self.make_parent("other@t.test")
        c = self.as_user(other)
        self.assertEqual(self.results(c.get("/api/parent/introductions/")), [])
        self.assertEqual(c.get(f"/api/parent/introductions/{intro_id}/").status_code, 404)
        self.assertEqual(self.as_user(self.tutor_user).get("/api/parent/introductions/").status_code, 403)

    def test_parent_and_tutor_cannot_message_each_other_through_the_platform(self):
        for url in ("/api/messages/", "/api/parent/messages/", "/api/tutor/messages/"):
            self.assertEqual(self.as_user(self.parent).post(url, {"body": "hi"}, format="json").status_code, 404)


class PrivacyAndInquiryTests(BaseTestCase):
    def setUp(self):
        super().setUp()
        self.admin = self.make_admin()
        self.parent = self.make_parent("one@t.test")
        self.other = self.make_parent("two@t.test")

    def test_parent_inquiry_is_private_to_parent_and_admins(self):
        c = self.as_user(self.parent)
        res = c.post("/api/parent/inquiries/", {"category": "complaint", "message": "A private concern about a lesson."}, format="json")
        self.assertEqual(res.status_code, 201)
        iid = res.data["id"]
        inquiry = PersonalInquiry.objects.get(pk=iid)
        inquiry.internal_notes = "staff opinion"
        inquiry.save()

        mine = json.dumps(c.get(f"/api/parent/inquiries/{iid}/").data)
        self.assertNotIn("staff opinion", mine)
        self.assertNotIn("internal_notes", mine)

        other = self.as_user(self.other)
        self.assertEqual(other.get(f"/api/parent/inquiries/{iid}/").status_code, 404)
        self.assertEqual(self.results(other.get("/api/parent/inquiries/")), [])
        tutor_user, _ = self.make_tutor("nosy@t.test")
        self.assertEqual(self.as_user(tutor_user).get("/api/admin/inquiries/").status_code, 403)
        self.assertEqual(self.as_user(self.other).get(f"/api/admin/inquiries/{iid}/").status_code, 403)
        self.assertEqual(self.as_user(self.admin).get(f"/api/admin/inquiries/{iid}/").status_code, 200)

        # nothing from the inquiry appears on public pages
        for url in ("/api/tutors/", "/api/reference/"):
            self.assertNotIn("private concern", json.dumps(self.anonymous().get(url).data))

    def test_inquiry_about_a_tutor_and_admin_reply(self):
        _, tutor = self.make_tutor("asked@t.test")
        res = self.as_user(self.parent).post(
            "/api/parent/inquiries/", {"message": "Is this tutor suitable for exams?", "about_tutor": tutor.id}, format="json"
        )
        self.assertEqual(res.status_code, 201)
        iid = res.data["id"]
        reply = self.as_user(self.admin).post(f"/api/admin/inquiries/{iid}/respond/", {"response": "Yes, she has exam experience."}, format="json")
        self.assertEqual(reply.status_code, 200)
        mine = self.as_user(self.parent).get(f"/api/parent/inquiries/{iid}/")
        self.assertEqual(mine.data["admin_response"], "Yes, she has exam experience.")
        self.assertEqual(mine.data["status"], "awaiting_parent")

    def test_inquiry_can_be_converted_to_a_hidden_draft_request(self):
        iid = self.as_user(self.parent).post("/api/parent/inquiries/", {"message": "Please find me a tutor"}, format="json").data["id"]
        res = self.as_user(self.admin).post(f"/api/admin/inquiries/{iid}/convert-to-request/")
        self.assertEqual(res.status_code, 201)
        req = ParentRequest.objects.get(pk=res.data["request"])
        self.assertEqual((req.parent, req.source, req.status), (self.parent, "inquiry", "draft"))
        self.assertEqual(self.as_user(self.admin).post(f"/api/admin/inquiries/{iid}/convert-to-request/").status_code, 400)

    def test_notifications_are_private_and_generic(self):
        res = self.as_user(self.parent).post(
            "/api/parent/requests/", {"subject": self.math.id, "grade_level": self.g10.id, "teaching_mode": "online"}, format="json"
        )
        self.assertEqual(res.status_code, 201)
        mine = self.as_user(self.parent).get("/api/notifications/")
        self.assertEqual(mine.data["count"], 1)
        self.assertNotIn("0900000001", json.dumps(mine.data))
        self.assertEqual(self.as_user(self.other).get("/api/notifications/").data["count"], 0)
        admin_notes = self.as_user(self.admin).get("/api/notifications/")
        self.assertEqual(admin_notes.data["count"], 1)
        nid = mine.data["results"][0]["id"]
        self.assertEqual(self.as_user(self.other).post(f"/api/notifications/{nid}/read/").status_code, 404)
        self.assertEqual(self.as_user(self.parent).post(f"/api/notifications/{nid}/read/").data["is_read"], True)

    def test_admin_dashboard_numbers_come_from_the_database(self):
        c = self.as_user(self.admin)
        before = c.get("/api/admin/stats/").data
        self.assertEqual(before["total_parents"], 2)
        self.assertEqual(before["approved_tutors"], 0)
        self.make_tutor("counted@t.test")
        ParentRequest.objects.create(status="new", source="telephone", contact_name="x")
        after = c.get("/api/admin/stats/").data
        self.assertEqual(after["approved_tutors"], 1)
        self.assertEqual(after["new_requests"], 1)
        self.assertEqual(after["unresolved_phone_requests"], 1)
        self.assertEqual(c.get("/api/admin/reports/").status_code, 200)

    def test_reference_data_is_public_and_database_driven(self):
        res = self.anonymous().get("/api/reference/")
        self.assertEqual(res.status_code, 200)
        self.assertIn("Mathematics", [s["name"] for s in res.data["subjects"]])
        c = self.as_user(self.admin)
        self.assertEqual(c.post("/api/admin/subjects/", {"name": "Geometry"}, format="json").status_code, 201)
        self.assertIn("Geometry", [s["name"] for s in self.anonymous().get("/api/reference/").data["subjects"]])
        self.assertEqual(self.as_user(self.parent).post("/api/admin/subjects/", {"name": "Hack"}, format="json").status_code, 403)
