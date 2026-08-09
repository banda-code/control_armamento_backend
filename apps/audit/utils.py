from .models import AuditLog, AuditOutcome


def get_client_ip(request):
    if request is None:
        return None

    forwarded_for = request.META.get("HTTP_X_FORWARDED_FOR")

    if forwarded_for:
        return forwarded_for.split(",")[0].strip()

    return request.META.get("REMOTE_ADDR")


def log_event(
    request,
    action,
    actor=None,
    target=None,
    unit=None,
    outcome=AuditOutcome.SUCCESS,
    metadata=None,
):
    if actor is None and request is not None:
        request_user = getattr(request, "user", None)
        if getattr(request_user, "is_authenticated", False):
            actor = request_user

    if unit is None and actor is not None:
        unit = getattr(actor, "unit", None)

    target_model = ""
    target_id = ""
    target_repr = ""

    if target is not None:
        target_model = target._meta.label
        target_id = str(target.pk)
        target_repr = str(target)[:255]

    user_agent = ""
    if request is not None:
        user_agent = request.META.get("HTTP_USER_AGENT", "")[:2000]

    return AuditLog.objects.create(
        actor=actor,
        unit=unit,
        action=action,
        outcome=outcome,
        target_model=target_model,
        target_id=target_id,
        target_repr=target_repr,
        ip_address=get_client_ip(request),
        user_agent=user_agent,
        metadata=metadata or {},
    )
