from django.conf import settings
from django.utils import timezone
from rest_framework_simplejwt.token_blacklist.models import (
    BlacklistedToken,
    OutstandingToken,
)
from rest_framework_simplejwt.tokens import RefreshToken

from .scopes import get_user_unit_id


def create_refresh_token_for_user(user):
    refresh = RefreshToken.for_user(user)

    unit_id = get_user_unit_id(user)

    refresh["role"] = user.role
    refresh["unit_id"] = (
        str(unit_id)
        if unit_id
        else None
    )
    refresh["global_scope"] = user.has_global_scope
    refresh["must_change_password"] = (
        user.must_change_password
    )

    return refresh


def set_refresh_cookie(response, refresh_token):
    max_age = int(
        settings.SIMPLE_JWT[
            "REFRESH_TOKEN_LIFETIME"
        ].total_seconds()
    )

    response.set_cookie(
        key=settings.JWT_REFRESH_COOKIE_NAME,
        value=str(refresh_token),
        max_age=max_age,
        httponly=settings.JWT_COOKIE_HTTPONLY,
        secure=settings.JWT_COOKIE_SECURE,
        samesite=settings.JWT_COOKIE_SAMESITE,
        domain=settings.JWT_COOKIE_DOMAIN or None,
        path=settings.JWT_COOKIE_PATH,
    )


def delete_refresh_cookie(response):
    response.delete_cookie(
        key=settings.JWT_REFRESH_COOKIE_NAME,
        domain=settings.JWT_COOKIE_DOMAIN or None,
        path=settings.JWT_COOKIE_PATH,
        samesite=settings.JWT_COOKIE_SAMESITE,
    )


def blacklist_all_refresh_tokens(user):
    outstanding_tokens = OutstandingToken.objects.filter(
        user=user,
        expires_at__gt=timezone.now(),
    )

    for token in outstanding_tokens:
        BlacklistedToken.objects.get_or_create(
            token=token
        )