from django.db import models


class Location(models.Model):
    """Country / city / area. Seeded with Addis Ababa sub-cities; extendable to other cities."""

    country = models.CharField(max_length=100, default="Ethiopia")
    city = models.CharField(max_length=100)
    area = models.CharField(max_length=100, blank=True)
    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ["country", "city", "area"]
        constraints = [models.UniqueConstraint(fields=["country", "city", "area"], name="uniq_location")]
        indexes = [models.Index(fields=["city", "area"])]

    def __str__(self):
        return f"{self.area}, {self.city}" if self.area else self.city


class Subject(models.Model):
    name = models.CharField(max_length=100, unique=True)
    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ["name"]

    def __str__(self):
        return self.name


class GradeLevel(models.Model):
    name = models.CharField(max_length=60, unique=True)
    order = models.PositiveSmallIntegerField(default=0)
    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ["order", "name"]

    def __str__(self):
        return self.name
