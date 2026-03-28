from django.urls import path

from .views import (
    UserLoginView,
    UserLogoutView,
    UserPasswordResetCompleteView,
    UserPasswordResetConfirmView,
    UserPasswordResetDoneView,
    UserPasswordResetView,
    activate_account_view,
    dashboard_view,
    home_view,
    profile_view,
    signup_done_view,
    signup_view,
)

urlpatterns = [
    path("", home_view, name="home"),
    path("rejestracja/", signup_view, name="signup"),
    path("rejestracja/sukces/", signup_done_view, name="signup_done"),
    path("logowanie/", UserLoginView.as_view(), name="login"),
    path("wylogowanie/", UserLogoutView.as_view(), name="logout"),
    path("profil/", profile_view, name="profile"),
    path("dashboard/", dashboard_view, name="dashboard"),
    path(
        "reset-hasla/",
        UserPasswordResetView.as_view(),
        name="password_reset",
    ),
    path(
        "reset-hasla/wyslano/",
        UserPasswordResetDoneView.as_view(),
        name="password_reset_done",
    ),
    path(
        "reset-hasla/<uidb64>/<token>/",
        UserPasswordResetConfirmView.as_view(),
        name="password_reset_confirm",
    ),
    path(
        "reset-hasla/gotowe/",
        UserPasswordResetCompleteView.as_view(),
        name="password_reset_complete",
    ),
    path(
        "aktywacja/<uidb64>/<token>/",
        activate_account_view,
        name="activate_account",
    ),
]
