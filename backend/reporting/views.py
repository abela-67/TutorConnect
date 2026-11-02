from datetime import timedelta

from django.db.models import Count
from django.db.models.functions import TruncDate
from django.utils import timezone
from django.utils.dateparse import parse_date
from rest_framework.response import Response
from rest_framework.views import APIView

from accounts.models import User
from accounts.permissions import IsAdminRole
from inquiries.models import PersonalInquiry
from introductions.models import Introduction
from jobs.models import JobApplication, TutoringJob
from tutor_requests.models import ParentRequest
from tutors.models import TutorDocument, TutorProfile


class StatsView(APIView):
    """Dashboard counters. Every number is computed from live database records."""

    permission_classes = [IsAdminRole]

    def get(self, request):
        open_requests = ParentRequest.objects.exclude(status__in=ParentRequest.CLOSED_STATUSES).exclude(status="draft")
        return Response(
            {
                "total_parents": User.objects.filter(role=User.Role.PARENT).count(),
                "total_tutors": TutorProfile.objects.count(),
                "approved_tutors": TutorProfile.objects.public().count(),
                "pending_tutor_applications": TutorProfile.objects.filter(status=TutorProfile.Status.UNDER_REVIEW).count(),
                "tutors_with_changes_to_review": TutorProfile.objects.filter(status="approved", has_unreviewed_changes=True).count(),
                "pending_documents": TutorDocument.objects.filter(status=TutorDocument.Status.PENDING).count(),
                "new_requests": ParentRequest.objects.filter(status=ParentRequest.Status.NEW).count(),
                "open_requests": open_requests.count(),
                "unresolved_phone_requests": ParentRequest.objects.filter(source=ParentRequest.Source.TELEPHONE).exclude(status__in=ParentRequest.CLOSED_STATUSES).count(),
                "draft_requests": ParentRequest.objects.filter(status="draft").count(),
                "open_jobs": TutoringJob.objects.filter(status__in=TutoringJob.ACCEPTING).count(),
                "pending_job_applications": JobApplication.objects.filter(status__in=["submitted", "under_review"]).count(),
                "introductions_awaiting_completion": Introduction.objects.exclude(status__in=["completed", "cancelled", "closed"]).count(),
                "new_inquiries": PersonalInquiry.objects.filter(status=PersonalInquiry.Status.NEW).count(),
            }
        )


def _group(qs, field):
    return {row[field] or "unknown": row["n"] for row in qs.values(field).annotate(n=Count("id")).order_by()}


class ReportsView(APIView):
    """Operational summary for a date range (defaults to the last 30 days)."""

    permission_classes = [IsAdminRole]

    def get(self, request):
        today = timezone.localdate()
        end = parse_date(request.query_params.get("end", "")) or today
        start = parse_date(request.query_params.get("start", "")) or (end - timedelta(days=30))
        if start > end:
            start, end = end, start

        def in_range(qs, field="created_at"):
            return qs.filter(**{f"{field}__date__gte": start, f"{field}__date__lte": end})

        requests = in_range(ParentRequest.objects.exclude(status="draft"))
        jobs = in_range(TutoringJob.objects.all())
        apps = in_range(JobApplication.objects.all())
        intros = in_range(Introduction.objects.all())

        per_day = (
            requests.annotate(day=TruncDate("created_at")).values("day").annotate(n=Count("id")).order_by("day")
        )
        top_subjects = (
            requests.exclude(subject__isnull=True).values("subject__name").annotate(n=Count("id")).order_by("-n")[:10]
        )
        tutors_per_subject = (
            TutorProfile.objects.public().values("subjects__name").annotate(n=Count("id", distinct=True)).exclude(subjects__name=None).order_by("-n")[:15]
        )
        return Response(
            {
                "range": {"start": start, "end": end},
                "requests_by_status": _group(requests, "status"),
                "requests_by_source": _group(requests, "source"),
                "requests_per_day": [{"date": r["day"], "count": r["n"]} for r in per_day],
                "top_requested_subjects": [{"subject": r["subject__name"], "count": r["n"]} for r in top_subjects],
                "jobs_by_status": _group(jobs, "status"),
                "applications_by_status": _group(apps, "status"),
                "introductions_by_status": _group(intros, "status"),
                "tutors_by_status": _group(TutorProfile.objects.all(), "status"),
                "approved_tutors_per_subject": [{"subject": r["subjects__name"], "count": r["n"]} for r in tutors_per_subject],
            }
        )
