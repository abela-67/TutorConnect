from django.contrib import admin

from .models import JobApplication, TutoringJob

admin.site.register(TutoringJob)
admin.site.register(JobApplication)
