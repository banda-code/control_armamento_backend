from django.conf import settings
from django.contrib.auth import authenticate
from django.contrib.auth.models import update_last_login
from django.contrib.auth.tokens import default_token_generator
from django.core.mail import send_mail
from django.utils.encoding import force_bytes, force_str
from django.utils.http import (
    urlsafe_base64_decode,
    urlsafe_base64_encode,
)
from django.utils.decorators import method_decorator
from django.views.decorators.csrf import ensure_csrf_cookie

from drf_spectacular.utils import extend_schema
from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.throttling import ScopedRateThrottle
from rest_framework.views import APIView
from rest_framework_simplejwt.authentication import JWTAuthentication
from rest_framework_simplejwt.exceptions import TokenError
from rest_framework_simplejwt.serializers import TokenRefreshSerializer
from rest_framework_simplejwt.tokens import RefreshToken

from apps.audit.models import AuditOutcome
from apps.audit.utils import log_event

from .authentication import CsrfEnforcedSessionAuthentication
from .jwt import (
    blacklist_all_refresh_tokens,
    create_refresh_token_for_user,
    delete_refresh_cookie,
    set_refresh_cookie,
)
from .models import User
from .permissions import IsAdministrator
from .scopes import get_user_unit
from .serializers import (
    DetailResponseSerializer,
    JwtLoginResponseSerializer,
    JwtRefreshResponseSerializer,
    LoginSerializer,
    PasswordChangeSerializer,
    PasswordResetConfirmSerializer,
    PasswordResetRequestSerializer,
    TemporaryPasswordSerializer,
    UserCreateSerializer,
    UserSerializer,
    UserUpdateSerializer,
)


@method_decorator(ensure_csrf_cookie, name="dispatch")
class CsrfCookieView(APIView):
    permission_classes = [AllowAny]
    authentication_classes = []

    @extend_schema(
        responses={
            200: DetailResponseSerializer,
        },
        auth=[],
        description=(
            "Configura la cookie CSRF necesaria para "
            "las operaciones públicas protegidas."
        ),
    )
    def get(self, request):
        return Response(
            {
                "detail": (
                    "Cookie CSRF configurada correctamente."
                )
            }
        )


class JwtLoginView(APIView):
    permission_classes = [AllowAny]
    authentication_classes = [
        CsrfEnforcedSessionAuthentication,
    ]
    throttle_classes = [ScopedRateThrottle]
    throttle_scope = "login"
    @extend_schema(
        request=LoginSerializer,
        responses={
            200: JwtLoginResponseSerializer,
            401: DetailResponseSerializer,
        },
        auth=[],
        description=(
            "Inicia sesión con el correo institucional "
            "y la contraseña del usuario."
        ),
    )
    def post(self, request):
        serializer = LoginSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        email = serializer.validated_data["email"]
        password = serializer.validated_data["password"]

        user = authenticate(
            request=request,
            email=email,
            password=password,
        )

        if user is None:
            log_event(
                request=request,
                action="LOGIN_FAILED",
                outcome=AuditOutcome.FAILED,
                metadata={"email": email},
            )
            return Response(
                {
                    "detail": (
                        "Las credenciales son incorrectas "
                        "o la cuenta está inactiva."
                    )
                },
                status=status.HTTP_401_UNAUTHORIZED,
            )

        refresh = create_refresh_token_for_user(user)
        access = refresh.access_token

        update_last_login(None, user)

        log_event(
            request=request,
            action="LOGIN_SUCCESS",
            actor=user,
            target=user,
            unit=get_user_unit(user),
            metadata={"authentication": "JWT"},
        )

        response = Response(
            {
                "detail": "Inicio de sesión correcto.",
                "access": str(access),
                "token_type": "Bearer",
                "expires_in": int(
                    settings.SIMPLE_JWT[
                        "ACCESS_TOKEN_LIFETIME"
                    ].total_seconds()
                ),
                "must_change_password": (
                    user.must_change_password
                ),
                "user": UserSerializer(user).data,
            },
            status=status.HTTP_200_OK,
        )
        set_refresh_cookie(response, refresh)
        return response


class JwtRefreshView(APIView):
    permission_classes = [AllowAny]
    authentication_classes = [
        CsrfEnforcedSessionAuthentication,
    ]
    throttle_classes = [ScopedRateThrottle]
    throttle_scope = "jwt_refresh"

    @extend_schema(
        request=None,
        responses={
            200: JwtRefreshResponseSerializer,
            401: DetailResponseSerializer,
        },
        auth=[],
        description=(
            "Renueva el access token utilizando "
            "el refresh token almacenado en una cookie HttpOnly."
        ),
    )
    def post(self, request):
        refresh_cookie = request.COOKIES.get(
            settings.JWT_REFRESH_COOKIE_NAME
        )

        if not refresh_cookie:
            return Response(
                {"detail": "No se encontró el refresh token."},
                status=status.HTTP_401_UNAUTHORIZED,
            )

        user = None
        try:
            parsed_refresh = RefreshToken(refresh_cookie)
            user = User.objects.filter(
                pk=parsed_refresh["user_id"]
            ).first()
        except (TokenError, KeyError):
            pass

        serializer = TokenRefreshSerializer(
            data={"refresh": refresh_cookie}
        )

        try:
            serializer.is_valid(raise_exception=True)
        except Exception:
            log_event(
                request=request,
                action="JWT_REFRESH_FAILED",
                actor=user,
                target=user,
                unit=get_user_unit(user),
                outcome=AuditOutcome.FAILED,
            )
            response = Response(
                {
                    "detail": (
                        "El refresh token venció, fue revocado "
                        "o no es válido."
                    )
                },
                status=status.HTTP_401_UNAUTHORIZED,
            )
            delete_refresh_cookie(response)
            return response

        response = Response(
            {
                "access": serializer.validated_data["access"],
                "token_type": "Bearer",
                "expires_in": int(
                    settings.SIMPLE_JWT[
                        "ACCESS_TOKEN_LIFETIME"
                    ].total_seconds()
                ),
            }
        )

        rotated_refresh = serializer.validated_data.get(
            "refresh"
        )
        if rotated_refresh:
            set_refresh_cookie(response, rotated_refresh)

        log_event(
            request=request,
            action="JWT_REFRESH_SUCCESS",
            actor=user,
            target=user,
            unit=get_user_unit(user),
        )

        return response


class JwtLogoutView(APIView):
    permission_classes = [AllowAny]
    authentication_classes = [
        CsrfEnforcedSessionAuthentication,
    ]

    @extend_schema(
        request=None,
        responses={
            200: DetailResponseSerializer,
        },
        auth=[],
        description=(
            "Cierra la sesión, revoca el refresh token "
            "y elimina la cookie de autenticación."
        ),
    )
    def post(self, request):
        refresh_cookie = request.COOKIES.get(
            settings.JWT_REFRESH_COOKIE_NAME
        )
        user = None
        outcome = AuditOutcome.SUCCESS

        if refresh_cookie:
            try:
                refresh = RefreshToken(refresh_cookie)
                user = User.objects.filter(
                    pk=refresh["user_id"]
                ).first()
                refresh.blacklist()
            except (TokenError, KeyError):
                outcome = AuditOutcome.FAILED

        log_event(
            request=request,
            action="LOGOUT",
            actor=user,
            target=user,
            unit=get_user_unit(user),
            outcome=outcome,
            metadata={"authentication": "JWT"},
        )

        response = Response(
            {"detail": "Sesión cerrada correctamente."}
        )
        delete_refresh_cookie(response)
        return response


class CurrentUserView(APIView):
    permission_classes = [IsAuthenticated]
    authentication_classes = [JWTAuthentication]
    @extend_schema(
        responses={
            200: UserSerializer,
        },
        description=(
            "Devuelve los datos del usuario autenticado."
        ),
    )

    def get(self, request):
        return Response(UserSerializer(request.user).data)


class PasswordChangeView(APIView):
    permission_classes = [IsAuthenticated]
    authentication_classes = [JWTAuthentication]
    @extend_schema(
        request=PasswordChangeSerializer,
        responses={
            200: DetailResponseSerializer,
            400: DetailResponseSerializer,
        },
        description=(
            "Cambia la contraseña del usuario autenticado "
            "y revoca sus sesiones activas."
        ),
    )

    def post(self, request):
        serializer = PasswordChangeSerializer(
            data=request.data,
            context={"request": request},
        )
        serializer.is_valid(raise_exception=True)

        user = request.user

        if not user.check_password(
            serializer.validated_data["old_password"]
        ):
            return Response(
                {
                    "old_password": [
                        "La contraseña actual es incorrecta."
                    ]
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        user.set_password(
            serializer.validated_data["new_password"]
        )
        user.must_change_password = False
        user.save(
            update_fields=[
                "password",
                "must_change_password",
                "updated_at",
            ]
        )

        blacklist_all_refresh_tokens(user)

        log_event(
            request=request,
            action="PASSWORD_CHANGED",
            actor=user,
            target=user,
            unit=get_user_unit(user),
        )

        response = Response(
            {
                "detail": (
                    "Contraseña actualizada. "
                    "Debe iniciar sesión nuevamente."
                )
            }
        )
        delete_refresh_cookie(response)
        return response


class PasswordResetRequestView(APIView):
    permission_classes = [AllowAny]
    authentication_classes = [
        CsrfEnforcedSessionAuthentication,
    ]
    throttle_classes = [ScopedRateThrottle]
    throttle_scope = "password_reset"

    generic_response = {
        "detail": (
            "Si el correo está registrado, recibirá "
            "las instrucciones de recuperación."
        )
    }
    @extend_schema(
        request=PasswordResetRequestSerializer,
        responses={
            200: DetailResponseSerializer,
        },
        auth=[],
        description=(
            "Solicita el envío de un enlace para "
            "restablecer la contraseña."
        ),
    )
    def post(self, request):
        serializer = PasswordResetRequestSerializer(
            data=request.data
        )
        serializer.is_valid(raise_exception=True)

        email = serializer.validated_data["email"]
        user = User.objects.filter(
            email=email,
            is_active=True,
        ).first()

        if not user:
            log_event(
                request=request,
                action="PASSWORD_RESET_REQUESTED",
                metadata={
                    "email": email,
                    "user_found": False,
                },
            )
            return Response(self.generic_response)

        uid = urlsafe_base64_encode(force_bytes(user.pk))
        token = default_token_generator.make_token(user)

        reset_url = (
            f"{settings.FRONTEND_PASSWORD_RESET_URL}"
            f"?uid={uid}&token={token}"
        )

        subject = (
            "Restablecimiento de contraseña - "
            "Sistema de Control de Armamento"
        )
        message = (
            f"Se solicitó restablecer la contraseña de "
            f"{user.email}.\n\n"
            f"Abra el siguiente enlace:\n{reset_url}\n\n"
            "El enlace es temporal. Si usted no realizó esta "
            "solicitud, comuníquese con el administrador."
        )

        try:
            send_mail(
                subject=subject,
                message=message,
                from_email=settings.DEFAULT_FROM_EMAIL,
                recipient_list=[user.email],
                fail_silently=False,
            )
            outcome = AuditOutcome.SUCCESS
        except Exception:
            outcome = AuditOutcome.FAILED

        log_event(
            request=request,
            action="PASSWORD_RESET_REQUESTED",
            actor=user,
            target=user,
            unit=get_user_unit(user),
            outcome=outcome,
            metadata={
                "email": email,
                "user_found": True,
            },
        )

        return Response(self.generic_response)


class PasswordResetConfirmView(APIView):
    permission_classes = [AllowAny]
    authentication_classes = [
        CsrfEnforcedSessionAuthentication,
    ]
    @extend_schema(
        request=PasswordResetConfirmSerializer,
        responses={
            200: DetailResponseSerializer,
            400: DetailResponseSerializer,
        },
        auth=[],
        description=(
            "Confirma el token de recuperación "
            "y establece una nueva contraseña."
        ),
    )
    def post(self, request):
        serializer = PasswordResetConfirmSerializer(
            data=request.data
        )
        serializer.is_valid(raise_exception=True)

        uid = serializer.validated_data["uid"]
        token = serializer.validated_data["token"]
        new_password = serializer.validated_data[
            "new_password"
        ]

        try:
            user_id = force_str(urlsafe_base64_decode(uid))
            user = User.objects.get(
                pk=user_id,
                is_active=True,
            )
        except (
            TypeError,
            ValueError,
            OverflowError,
            User.DoesNotExist,
        ):
            return Response(
                {"detail": "El enlace no es válido."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        if not default_token_generator.check_token(user, token):
            log_event(
                request=request,
                action="PASSWORD_RESET_FAILED",
                actor=user,
                target=user,
                unit=get_user_unit(user),
                outcome=AuditOutcome.FAILED,
            )
            return Response(
                {
                    "detail": (
                        "El enlace venció o ya fue utilizado."
                    )
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        user.set_password(new_password)
        user.must_change_password = False
        user.save(
            update_fields=[
                "password",
                "must_change_password",
                "updated_at",
            ]
        )
        blacklist_all_refresh_tokens(user)

        log_event(
            request=request,
            action="PASSWORD_RESET_COMPLETED",
            actor=user,
            target=user,
            unit=get_user_unit(user),
        )

        response = Response(
            {"detail": "Contraseña restablecida correctamente."}
        )
        delete_refresh_cookie(response)
        return response


class UserViewSet(viewsets.ModelViewSet):
    permission_classes = [IsAdministrator]
    authentication_classes = [JWTAuthentication]
    queryset = User.objects.select_related(
        "personnel",
        "personnel__rank",
        "personnel__position",
        "personnel__unit",
        "personnel__section",
        "created_by",
    ).all()
    http_method_names = [
        "get",
        "post",
        "patch",
        "head",
        "options",
    ]

    def get_serializer_class(self):
        if self.action == "create":
            return UserCreateSerializer
        if self.action in {"partial_update", "update"}:
            return UserUpdateSerializer
        if self.action == "temporary_password":
            return TemporaryPasswordSerializer
        return UserSerializer

    @action(
        detail=True,
        methods=["post"],
        url_path="activate",
    )
    def activate(self, request, pk=None):
        user = self.get_object()
        user.is_active = True
        user.save(update_fields=["is_active", "updated_at"])

        log_event(
            request=request,
            action="USER_ACTIVATED",
            actor=request.user,
            target=user,
            unit=get_user_unit(user),
        )

        return Response(UserSerializer(user).data)

    @action(
        detail=True,
        methods=["post"],
        url_path="deactivate",
    )
    def deactivate(self, request, pk=None):
        user = self.get_object()

        if user.pk == request.user.pk:
            return Response(
                {
                    "detail": (
                        "No puede desactivar su propia cuenta."
                    )
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        user.is_active = False
        user.save(update_fields=["is_active", "updated_at"])
        blacklist_all_refresh_tokens(user)

        log_event(
            request=request,
            action="USER_DEACTIVATED",
            actor=request.user,
            target=user,
            unit=get_user_unit(user),
        )

        return Response(UserSerializer(user).data)

    @action(
        detail=True,
        methods=["post"],
        url_path="temporary-password",
    )
    def temporary_password(self, request, pk=None):
        user = self.get_object()
        serializer = TemporaryPasswordSerializer(
            data=request.data
        )
        serializer.is_valid(raise_exception=True)

        user.set_password(
            serializer.validated_data[
                "temporary_password"
            ]
        )
        user.must_change_password = True
        user.save(
            update_fields=[
                "password",
                "must_change_password",
                "updated_at",
            ]
        )
        blacklist_all_refresh_tokens(user)

        log_event(
            request=request,
            action="TEMPORARY_PASSWORD_ASSIGNED",
            actor=request.user,
            target=user,
            unit=get_user_unit(user),
        )

        return Response(
            {
                "detail": (
                    "Contraseña temporal asignada. "
                    "El usuario deberá cambiarla al ingresar."
                )
            }
        )
