from django.urls import path
from rest_framework.routers import DefaultRouter

from .views import (
    CsrfCookieView,
    CurrentUserView,
    JwtLoginView,
    JwtLogoutView,
    JwtRefreshView,
    PasswordChangeView,
    PasswordResetConfirmView,
    PasswordResetRequestView,
    UserViewSet,
)


router = DefaultRouter()
router.register("users", UserViewSet, basename="user")

urlpatterns = [
    path("auth/csrf/", CsrfCookieView.as_view(), name="auth-csrf"),
    path("auth/login/", JwtLoginView.as_view(), name="auth-login"),
    path(
        "auth/token/refresh/",
        JwtRefreshView.as_view(),
        name="jwt-refresh",
    ),
    path("auth/logout/", JwtLogoutView.as_view(), name="auth-logout"),
    path("auth/me/", CurrentUserView.as_view(), name="auth-me"),
    path(
        "auth/password/change/",
        PasswordChangeView.as_view(),
        name="password-change",
    ),
    path(
        "auth/password/reset/",
        PasswordResetRequestView.as_view(),
        name="password-reset",
    ),
    path(
        "auth/password/reset/confirm/",
        PasswordResetConfirmView.as_view(),
        name="password-reset-confirm",
    ),
]

urlpatterns += router.urls
