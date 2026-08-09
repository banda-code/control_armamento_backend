from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin

from .forms import UserChangeForm, UserCreationForm
from .models import User


@admin.register(User)
class UserAdmin(BaseUserAdmin):
    form = UserChangeForm
    add_form = UserCreationForm

    list_display = (
        "email",
        "personnel_tin",
        "personnel_full_name",
        "role",
        "personnel_unit",
        "is_active",
        "is_staff",
    )

    list_filter = (
        "role",
        "personnel__unit",
        "is_active",
        "is_staff",
        "is_superuser",
    )

    search_fields = (
        "email",
        "personnel__tin",
        "personnel__first_name",
        "personnel__paternal_last_name",
        "personnel__maternal_last_name",
    )

    ordering = (
        "personnel__paternal_last_name",
        "personnel__first_name",
        "email",
    )

    readonly_fields = (
        "last_login",
        "created_at",
        "updated_at",
        "personnel_tin",
        "personnel_full_name",
        "personnel_rank",
        "personnel_position",
        "personnel_unit",
        "personnel_section",
    )

    autocomplete_fields = (
        "created_by",
    )

    fieldsets = (
        (
            "Acceso",
            {
                "fields": (
                    "email",
                    "password",
                    "personnel",
                )
            },
        ),
        (
            "Personal militar asociado",
            {
                "fields": (
                    "personnel_tin",
                    "personnel_full_name",
                    "personnel_rank",
                    "personnel_position",
                    "personnel_unit",
                    "personnel_section",
                )
            },
        ),
        (
            "Rol y estado de la cuenta",
            {
                "fields": (
                    "role",
                    "must_change_password",
                    "is_active",
                    "is_staff",
                    "is_superuser",
                    "groups",
                    "user_permissions",
                )
            },
        ),
        (
            "Auditoría",
            {
                "fields": (
                    "created_by",
                    "last_login",
                    "created_at",
                    "updated_at",
                )
            },
        ),
    )

    add_fieldsets = (
        (
            "Nueva cuenta de usuario",
            {
                "classes": ("wide",),
                "fields": (
                    "email",
                    "personnel",
                    "role",
                    "password1",
                    "password2",
                    "is_active",
                ),
            },
        ),
    )

    def get_queryset(self, request):
        return super().get_queryset(request).select_related(
            "personnel",
            "personnel__rank",
            "personnel__position",
            "personnel__unit",
            "personnel__section",
        )

    @admin.display(
        description="TIN",
        ordering="personnel__tin",
    )
    def personnel_tin(self, obj):
        if not obj.personnel:
            return "-"
        return obj.personnel.tin

    @admin.display(
        description="Personal militar",
        ordering="personnel__paternal_last_name",
    )
    def personnel_full_name(self, obj):
        if not obj.personnel:
            return "-"
        return obj.personnel.full_name

    @admin.display(
        description="Grado",
        ordering="personnel__rank__name",
    )
    def personnel_rank(self, obj):
        if not obj.personnel or not obj.personnel.rank:
            return "-"
        return obj.personnel.rank

    @admin.display(
        description="Cargo",
        ordering="personnel__position__name",
    )
    def personnel_position(self, obj):
        if not obj.personnel or not obj.personnel.position:
            return "-"
        return obj.personnel.position

    @admin.display(
        description="Unidad",
        ordering="personnel__unit__name",
    )
    def personnel_unit(self, obj):
        if not obj.personnel or not obj.personnel.unit:
            return "-"
        return obj.personnel.unit

    @admin.display(
        description="Sección",
        ordering="personnel__section__name",
    )
    def personnel_section(self, obj):
        if not obj.personnel or not obj.personnel.section:
            return "-"
        return obj.personnel.section