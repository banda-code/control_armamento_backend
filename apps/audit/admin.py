from django.contrib import admin

from .models import AuditLog


@admin.register(AuditLog)
class AuditLogAdmin(admin.ModelAdmin):
    list_display = (
        "created_at",
        "action",
        "outcome",
        "actor",
        "unit",
        "target_repr",
        "ip_address",
    )
    list_filter = (
        "action",
        "outcome",
        "unit",
        "created_at",
    )
    search_fields = (
        "actor__email",
        "actor__personnel__tin",
        "target_repr",
        "ip_address",
    )
    readonly_fields = (
        "id",
        "actor",
        "unit",
        "action",
        "outcome",
        "target_model",
        "target_id",
        "target_repr",
        "ip_address",
        "user_agent",
        "metadata",
        "created_at",
    )

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False
