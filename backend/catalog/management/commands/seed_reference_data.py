from django.core.management.base import BaseCommand

from catalog.models import GradeLevel, Location, Subject

ADDIS_AREAS = [
    "Addis Ketema", "Akaki Kality", "Arada", "Bole", "Gulele",
    "Kirkos", "Kolfe Keranio", "Lideta", "Nifas Silk-Lafto", "Yeka", "Lemi Kura",
]

SUBJECTS = [
    "Mathematics", "Physics", "Chemistry", "Biology", "English", "Amharic", "Afaan Oromo",
    "French", "Arabic", "Computer Science", "Civics", "History", "Geography", "Economics",
    "Accounting", "General Science", "Social Studies",
]

GRADES = (
    ["KG"] + [f"Grade {n}" for n in range(1, 13)] + ["University / College", "Adult learner"]
)


class Command(BaseCommand):
    help = "Create the initial locations (Addis Ababa), subjects and grade levels. Safe to run repeatedly."

    def handle(self, *args, **options):
        for area in ADDIS_AREAS:
            Location.objects.get_or_create(country="Ethiopia", city="Addis Ababa", area=area)
        for name in SUBJECTS:
            Subject.objects.get_or_create(name=name)
        for order, name in enumerate(GRADES):
            GradeLevel.objects.get_or_create(name=name, defaults={"order": order})
        self.stdout.write(self.style.SUCCESS(
            f"Reference data ready: {Location.objects.count()} locations, "
            f"{Subject.objects.count()} subjects, {GradeLevel.objects.count()} grade levels."
        ))
