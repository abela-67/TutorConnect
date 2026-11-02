import django_filters as df
from django.db.models import Exists, OuterRef, Q

from .models import TutorAvailability, TutorProfile


class TutorFilter(df.FilterSet):
    """Public directory filters. All conditions are combined with AND and executed in the database."""

    gender = df.ChoiceFilter(choices=TutorProfile.Gender.choices, method="filter_gender")
    location = df.NumberFilter(field_name="location_id")
    city = df.CharFilter(field_name="location__city", lookup_expr="iexact")
    subject = df.NumberFilter(method="filter_subject")
    grade_level = df.NumberFilter(method="filter_grade")
    teaching_mode = df.ChoiceFilter(choices=[("online", "Online"), ("in_person", "In person")], method="filter_mode")
    min_experience = df.NumberFilter(field_name="years_experience", lookup_expr="gte")
    rate_unit = df.ChoiceFilter(choices=TutorProfile.RateUnit.choices)
    min_rate = df.NumberFilter(field_name="rate_amount", lookup_expr="gte")
    max_rate = df.NumberFilter(field_name="rate_amount", lookup_expr="lte")
    available_day = df.NumberFilter(method="filter_day", min_value=0, max_value=6)
    q = df.CharFilter(method="filter_q")

    class Meta:
        model = TutorProfile
        fields = []

    def filter_gender(self, qs, name, value):
        # Only tutors who chose to show their gender are searchable by it.
        return qs.filter(gender=value, show_gender=True)

    def filter_subject(self, qs, name, value):
        return qs.filter(subjects__id=value)

    def filter_grade(self, qs, name, value):
        return qs.filter(grade_levels__id=value)

    def filter_mode(self, qs, name, value):
        return qs.filter(teaching_mode__in=[value, TutorProfile.Mode.BOTH])

    def filter_day(self, qs, name, value):
        return qs.filter(Exists(TutorAvailability.objects.filter(tutor=OuterRef("pk"), weekday=value)))

    def filter_q(self, qs, name, value):
        value = value.strip()
        if not value:
            return qs
        return qs.filter(
            Q(display_name__icontains=value) | Q(bio__icontains=value) | Q(subjects__name__icontains=value)
        ).distinct()
