from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.urls import include, path

urlpatterns = [
    path("django-admin/", admin.site.urls),
    path("api/", include("accounts.urls")),
    path("api/", include("catalog.urls")),
    path("api/", include("tutors.urls")),
    path("api/", include("tutor_requests.urls")),
    path("api/", include("jobs.urls")),
    path("api/", include("introductions.urls")),
    path("api/", include("inquiries.urls")),
    path("api/", include("notifications.urls")),
    path("api/", include("audit.urls")),
    path("api/", include("reporting.urls")),
]

if settings.DEBUG:
    # Only public profile photos live under MEDIA_ROOT; tutor credentials are never exposed this way.
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
