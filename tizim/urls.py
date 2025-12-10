from django.urls import path

from . import views

urlpatterns = [
    path("", views.dashboard_view, name="dashboard"),
    path("register/", views.register_view, name="register"),
    path("login/", views.login_view, name="login"),
    path("logout/", views.logout_view, name="logout"),
    path("transfer/", views.transfer_view, name="transfer"),
    path("top-up/", views.top_up_view, name="top_up"),
    path("profile/", views.profile_view, name="profile"),
    path("docs/", views.docs_view, name="docs"),
]

