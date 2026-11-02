"""Candidate matching for administrators.

Matching *suggests* candidates and explains why; it never decides. Subject and (explicit) gender preference are
hard filters; everything else is scored so an administrator can still consider partial matches.
"""
from django.db.models import Count, Q

from .models import TutorProfile


def candidate_queryset():
    return (
        TutorProfile.objects.public()
        .select_related("location", "user")
        .prefetch_related("subjects", "grade_levels", "availability", "qualifications")
        .annotate(verified_docs=Count("documents", filter=Q(documents__status="verified"), distinct=True))
    )


def _mode_compatible(wanted, tutor_mode):
    if wanted in (None, "", "either"):
        return True
    return tutor_mode == "both" or tutor_mode == wanted


def find_candidates(*, subject=None, grade_level=None, location=None, mode="", gender="", budget=None, limit=30):
    qs = candidate_queryset()
    if subject:
        qs = qs.filter(subjects=subject)
    if gender:
        qs = qs.filter(gender=gender)

    results = []
    for tutor in qs[:300]:
        score = 0.0
        reasons, concerns = [], []

        if subject:
            score += 3
            reasons.append(f"Teaches {subject.name}")

        if grade_level:
            if any(g.pk == grade_level.pk for g in tutor.grade_levels.all()):
                score += 2
                reasons.append(f"Teaches {grade_level.name}")
            else:
                concerns.append(f"Does not list {grade_level.name}")

        if mode and mode != "either":
            if _mode_compatible(mode, tutor.teaching_mode):
                score += 1
                reasons.append("Teaching mode compatible")
            else:
                concerns.append("Teaching mode differs")

        if location and mode != "online":
            if tutor.location_id == location.pk:
                score += 2
                reasons.append(f"Based in {location}")
            elif tutor.location and tutor.location.city == location.city:
                score += 1
                reasons.append(f"Same city ({location.city})")
            else:
                concerns.append("Different area/city")

        if budget is not None and tutor.rate_amount is not None:
            if tutor.rate_amount <= budget:
                score += 1
                reasons.append("Rate within budget")
            else:
                concerns.append("Rate above budget (units may differ)")

        if tutor.verified_docs:
            score += 1
            reasons.append("Has reviewed credentials")
        if tutor.has_unreviewed_changes:
            concerns.append("Has changes awaiting review")

        results.append({"tutor": tutor, "score": score, "reasons": reasons, "concerns": concerns})

    results.sort(key=lambda r: (-r["score"], -r["tutor"].years_experience, r["tutor"].display_name))
    return results[:limit]
