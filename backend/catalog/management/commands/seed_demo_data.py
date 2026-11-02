"""DEVELOPMENT ONLY: creates fake demo accounts and tutors. Refuses to run unless DJANGO_DEBUG=True."""
from django.conf import settings
from django.core.management import call_command
from django.core.management.base import BaseCommand, CommandError
from django.utils import timezone

from accounts.models import ParentProfile, User
from catalog.models import GradeLevel, Location, Subject
from tutors.models import TutorAvailability, TutorProfile, TutorQualification

DEMO_PASSWORD = "DemoPass12345!"

TUTORS = [
    ("Selam Tesfaye", "female", "Bole", ["Mathematics", "Physics"], ["Grade 9", "Grade 10", "Grade 11", "Grade 12"], 6, "in_person", 400),
    ("Dawit Alemu", "male", "Kirkos", ["English", "Amharic"], ["Grade 5", "Grade 6", "Grade 7", "Grade 8"], 3, "both", 250),
    ("Hanna Bekele", "female", "Yeka", ["Chemistry", "Biology"], ["Grade 9", "Grade 10", "Grade 11", "Grade 12"], 8, "both", 450),
    ("Yonas Girma", "male", "Bole", ["Computer Science", "Mathematics"], ["Grade 11", "Grade 12", "University / College"], 5, "online", 500),
    ("Meron Abebe", "female", "Arada", ["English"], ["KG", "Grade 1", "Grade 2", "Grade 3", "Grade 4"], 2, "in_person", 200),
]


class Command(BaseCommand):
    help = "Create fake demo data (admin, parent, tutors). Development only."

    def handle(self, *args, **options):
        if not settings.DEBUG:
            raise CommandError("Demo data can only be created when DJANGO_DEBUG=True.")
        call_command("seed_reference_data")

        admin, _ = User.objects.get_or_create(email="admin@demo.test", defaults={"full_name": "Demo Admin", "role": "admin", "is_staff": True, "is_superuser": True})
        parent, created = User.objects.get_or_create(email="parent@demo.test", defaults={"full_name": "Demo Parent", "phone": "0900000000", "role": "parent"})
        for u in (admin, parent):
            u.set_password(DEMO_PASSWORD)
            u.save()
        ParentProfile.objects.get_or_create(user=parent)

        for name, gender, area, subjects, grades, years, mode, rate in TUTORS:
            email = name.lower().replace(" ", ".") + "@demo.test"
            user, _ = User.objects.get_or_create(email=email, defaults={"full_name": name, "phone": "0911000000", "role": "tutor"})
            user.set_password(DEMO_PASSWORD)
            user.save()
            profile, _ = TutorProfile.objects.get_or_create(user=user, defaults={"display_name": name})
            profile.gender, profile.years_experience, profile.teaching_mode = gender, years, mode
            profile.rate_amount, profile.rate_unit = rate, "hour"
            profile.location = Location.objects.filter(city="Addis Ababa", area=area).first()
            profile.bio = f"Demo profile for {name}. This is fictional sample data."
            profile.languages = ["Amharic", "English"]
            profile.status = "approved"
            profile.reviewed_by, profile.reviewed_at = admin, timezone.now()
            profile.save()
            profile.subjects.set(Subject.objects.filter(name__in=subjects))
            profile.grade_levels.set(GradeLevel.objects.filter(name__in=grades))
            if not profile.qualifications.exists():
                TutorQualification.objects.create(tutor=profile, level="bachelor", title="BSc (demo)", institution="Demo University", year=2018)
            if not profile.availability.exists():
                for day in (0, 2, 4):
                    TutorAvailability.objects.create(tutor=profile, weekday=day, start_time="16:00", end_time="19:00")

        self.stdout.write(self.style.SUCCESS(
            f"Demo data ready. Logins: admin@demo.test / parent@demo.test / selam.tesfaye@demo.test  password: {DEMO_PASSWORD}"
        ))
