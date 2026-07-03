# Root URL configuration.
#
# Story 1.2 adds /health/, Story 1.4 adds the /api/v1/ prefix and the SPA
# catch-all. For now only the admin site is wired.
from django.contrib import admin
from django.urls import path

urlpatterns = [
    path("admin/", admin.site.urls),
]
