from django.contrib import admin

from .models import TutorAvailability, TutorDocument, TutorProfile, TutorQualification


@admin.register(TutorProfile)
class TutorProfileAdmin(admin.ModelAdmin):
    list_display = ["display_name", "status", "location", "updated_at"]
    list_filter = ["status"]
    search_fields = ["display_name", "user__email"]


admin.site.register(TutorQualification)
admin.site.register(TutorAvailability)


@admin.register(TutorDocument)
class TutorDocumentAdmin(admin.ModelAdmin):
    # Files are intentionally not editable/downloadable here; use the authorised API endpoint.
    list_display = ["original_name", "tutor", "status", "uploaded_at"]
    exclude = ["file"]
    readonly_fields = ["original_name", "content_type", "size"]
