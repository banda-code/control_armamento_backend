from rest_framework.authentication import SessionAuthentication


class CsrfEnforcedSessionAuthentication(SessionAuthentication):
    """
    Fuerza la validación CSRF también en endpoints públicos como login
    y recuperación de contraseña.
    """

    def authenticate(self, request):
        self.enforce_csrf(request)
        return None
