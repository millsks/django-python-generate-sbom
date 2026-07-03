"""URL routes for the users app (mounted under /api/v1/auth/)."""

from django.urls import path

from .views import RegisterView

urlpatterns = [
    path("register/", RegisterView.as_view(), name="register"),
]
