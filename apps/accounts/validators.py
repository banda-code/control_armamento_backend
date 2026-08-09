from django.core.exceptions import ValidationError


INSTITUTIONAL_EMAIL_DOMAIN = "armada.mil.bo"


def normalize_institutional_email(email: str) -> str:
    return (email or "").strip().lower()


def validate_institutional_email(email: str) -> None:
    normalized = normalize_institutional_email(email)

    if not normalized.endswith(f"@{INSTITUTIONAL_EMAIL_DOMAIN}"):
        raise ValidationError(
            "Debe utilizar un correo institucional @armada.mil.bo."
        )

    local_part, separator, domain = normalized.rpartition("@")

    if not separator or not local_part or domain != INSTITUTIONAL_EMAIL_DOMAIN:
        raise ValidationError(
            "El correo institucional no tiene un formato válido."
        )
