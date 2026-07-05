"""URL routes for the users app (mounted under /api/v1/)."""

from django.urls import path

from .views import (
    AuthMeView,
    CreateOrgView,
    GrantGlobalAdminView,
    KeyDetailView,
    KeysView,
    LeaveOrgView,
    LoginView,
    LogoutView,
    MemberDetailView,
    MembersView,
    OrgListView,
    OrgMeView,
    OrgSwitchView,
    RegisterView,
    TransferAdminView,
)

urlpatterns = [
    path("auth/register/", RegisterView.as_view(), name="register"),
    path("auth/login/", LoginView.as_view(), name="login"),
    path("auth/logout/", LogoutView.as_view(), name="logout"),
    path("auth/me/", AuthMeView.as_view(), name="auth-me"),
    path("orgs/", OrgListView.as_view(), name="org-list"),
    path("orgs/create/", CreateOrgView.as_view(), name="org-create"),
    path("orgs/switch/", OrgSwitchView.as_view(), name="org-switch"),
    path("orgs/me/", OrgMeView.as_view(), name="org-me"),
    path("orgs/leave/", LeaveOrgView.as_view(), name="org-leave"),
    path("orgs/transfer-admin/", TransferAdminView.as_view(), name="org-transfer-admin"),
    path("orgs/members/", MembersView.as_view(), name="org-members"),
    path("orgs/members/<int:user_id>/", MemberDetailView.as_view(), name="org-member-detail"),
    path("keys/", KeysView.as_view(), name="key-list"),
    path("keys/<str:key_id>/", KeyDetailView.as_view(), name="key-detail"),
    path("admin/global-admins/", GrantGlobalAdminView.as_view(), name="grant-global-admin"),
]
