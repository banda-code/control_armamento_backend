from rest_framework import filters, generics
from rest_framework.permissions import IsAuthenticated

from apps.accounts.scopes import get_user_unit_id

from .models import AuditLog
from .serializers import AuditLogSerializer


class AuditLogListView(generics.ListAPIView):
    serializer_class = AuditLogSerializer
    permission_classes = [IsAuthenticated]

    filter_backends = [
        filters.SearchFilter,
        filters.OrderingFilter,
    ]

    search_fields = [
        "action",
        "actor__email",
        "actor__personnel__tin",
        "actor__personnel__first_name",
        "actor__personnel__paternal_last_name",
        "target_repr",
        "unit__name",
    ]

    ordering_fields = [
        "created_at",
        "action",
        "outcome",
    ]

    ordering = ["-created_at"]

    def get_queryset(self):
        queryset = AuditLog.objects.select_related(
            "actor",
            "actor__personnel",
            "unit",
        ).all()

        user = self.request.user

        # ---------------------------------------------
        # Alcance del usuario
        # ---------------------------------------------

        if user.has_global_scope:
            scoped_queryset = queryset

        else:
            unit_id = get_user_unit_id(user)

            if unit_id:
                scoped_queryset = queryset.filter(
                    unit_id=unit_id
                )
            else:
                scoped_queryset = queryset.filter(
                    actor=user
                )

        # ---------------------------------------------
        # Filtros opcionales
        # ---------------------------------------------

        action = self.request.query_params.get(
            "action"
        )

        outcome = self.request.query_params.get(
            "outcome"
        )

        unit_id = self.request.query_params.get(
            "unit"
        )

        actor_id = self.request.query_params.get(
            "actor"
        )

        if action:
            scoped_queryset = scoped_queryset.filter(
                action=action
            )

        if outcome:
            scoped_queryset = scoped_queryset.filter(
                outcome=outcome
            )

        # Solo un usuario con alcance global
        # puede consultar explícitamente otra unidad.
        if unit_id and user.has_global_scope:
            scoped_queryset = scoped_queryset.filter(
                unit_id=unit_id
            )

        if actor_id:
            scoped_queryset = scoped_queryset.filter(
                actor_id=actor_id
            )

        return scoped_queryset