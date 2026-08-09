from django.contrib import admin

from .models import Institution, Position, Rank, Section, Unit


@admin.register(Institution)
class InstitutionAdmin(admin.ModelAdmin):
    list_display = ("name", "acronym", "is_active")
    search_fields = ("name", "acronym")
    list_filter = ("is_active",)


@admin.register(Unit)
class UnitAdmin(admin.ModelAdmin):
    list_display = (
        "name",
        "acronym",
        "code",
        "institution",
        "parent",
        "is_active",
    )
    search_fields = ("name", "acronym", "code")
    list_filter = ("institution", "is_active")
    autocomplete_fields = ("institution", "parent")


@admin.register(Rank)
class RankAdmin(admin.ModelAdmin):
    list_display = (
        "order",
        "name",
        "abbreviation",
        "is_active",
    )
    search_fields = ("name", "abbreviation")
    list_filter = ("is_active",)
    ordering = ("order", "name")


@admin.register(Position)
class PositionAdmin(admin.ModelAdmin):
    list_display = ("name", "is_active")
    search_fields = ("name",)
    list_filter = ("is_active",)


@admin.register(Section)
class SectionAdmin(admin.ModelAdmin):
    list_display = ("name", "unit", "code", "is_active")
    search_fields = ("name", "code", "unit__name")
    list_filter = ("unit", "is_active")
    autocomplete_fields = ("unit",)
