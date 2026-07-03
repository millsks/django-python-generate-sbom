"""URL routes for the users app (mounted under /api/v1/)."""

from django.urls import path

from .views import (
    LoginView,
    LogoutView,
    OrgListView,
    OrgMeView,
    OrgSwitchView,
    RegisterView,
)

urlpatterns = [
    path("auth/register/", RegisterView.as_view(), name="register"),
    path("auth/login/", LoginView.as_view(), name="login"),
    path("auth/logout/", LogoutView.as_view(), name="logout"),
    path("orgs/", OrgListView.as_view(), name="org-list"),
    path("orgs/switch/", OrgSwitchView.as_view(), name="org-switch"),
    path("orgs/me/", OrgMeView.as_view(), name="org-me"),
]
