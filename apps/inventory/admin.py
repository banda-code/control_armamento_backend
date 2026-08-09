from django.contrib import admin

from apps.inventory.models import (
    Armory,
    Caliber,
    ComponentType,
    Country,
    Manufacturer,
    MaterialCategory,
    MaterialSpecification,
    MaterialType,
    SerializedMaterial,
    SerializedMaterialComponent,
    StockBatch,
    StockMaterial,
    UnitOfMeasure,
)


@admin.register(MaterialCategory)
class MaterialCategoryAdmin(admin.ModelAdmin):
    list_display = (
        "name",
        "code",
        "is_active",
        "created_at",
    )
    search_fields = (
        "name",
        "code",
    )
    list_filter = (
        "is_active",
    )
    ordering = (
        "name",
    )


@admin.register(MaterialType)
class MaterialTypeAdmin(admin.ModelAdmin):
    list_display = (
        "name",
        "category",
        "code",
        "control_method",
        "is_active",
    )
    search_fields = (
        "name",
        "code",
        "category__name",
    )
    list_filter = (
        "category",
        "control_method",
        "is_active",
    )
    autocomplete_fields = (
        "category",
    )


@admin.register(Manufacturer)
class ManufacturerAdmin(admin.ModelAdmin):
    list_display = (
        "name",
        "is_active",
        "created_at",
    )
    search_fields = (
        "name",
    )
    list_filter = (
        "is_active",
    )


@admin.register(Country)
class CountryAdmin(admin.ModelAdmin):
    list_display = (
        "name",
        "code",
        "is_active",
    )
    search_fields = (
        "name",
        "code",
    )
    list_filter = (
        "is_active",
    )


@admin.register(Caliber)
class CaliberAdmin(admin.ModelAdmin):
    list_display = (
        "name",
        "description",
        "is_active",
    )
    search_fields = (
        "name",
        "description",
    )
    list_filter = (
        "is_active",
    )


@admin.register(UnitOfMeasure)
class UnitOfMeasureAdmin(admin.ModelAdmin):
    list_display = (
        "name",
        "symbol",
        "allows_decimals",
        "is_active",
    )
    search_fields = (
        "name",
        "symbol",
    )
    list_filter = (
        "allows_decimals",
        "is_active",
    )


@admin.register(MaterialSpecification)
class MaterialSpecificationAdmin(admin.ModelAdmin):
    list_display = (
        "name",
        "material_type",
        "manufacturer",
        "country",
        "caliber",
        "is_active",
    )
    search_fields = (
        "name",
        "material_type__name",
        "manufacturer__name",
        "country__name",
        "caliber__name",
    )
    list_filter = (
        "material_type",
        "manufacturer",
        "country",
        "caliber",
        "is_active",
    )
    autocomplete_fields = (
        "material_type",
        "manufacturer",
        "country",
        "caliber",
    )


@admin.register(Armory)
class ArmoryAdmin(admin.ModelAdmin):
    list_display = (
        "name",
        "code",
        "unit",
        "is_active",
    )
    search_fields = (
        "name",
        "code",
        "unit__name",
    )
    list_filter = (
        "unit",
        "is_active",
    )
    autocomplete_fields = (
        "unit",
    )


class SerializedMaterialComponentInline(admin.TabularInline):
    model = SerializedMaterialComponent
    extra = 0
    fields = (
        "component_type",
        "identification_number",
        "quantity",
        "observations",
        "is_active",
    )
    autocomplete_fields = (
        "component_type",
    )


@admin.register(SerializedMaterial)
class SerializedMaterialAdmin(admin.ModelAdmin):
    list_display = (
        "institutional_code",
        "identification_number",
        "specification",
        "unit",
        "armory",
        "status",
        "physical_condition",
        "is_active",
    )
    search_fields = (
        "institutional_code",
        "identification_number",
        "specification__name",
        "specification__material_type__name",
        "unit__name",
        "armory__name",
    )
    list_filter = (
        "status",
        "physical_condition",
        "unit",
        "armory",
        "is_active",
    )
    autocomplete_fields = (
        "specification",
        "unit",
        "armory",
        "created_by",
        "updated_by",
    )
    readonly_fields = (
        "created_at",
        "updated_at",
    )
    inlines = (
        SerializedMaterialComponentInline,
    )


@admin.register(StockMaterial)
class StockMaterialAdmin(admin.ModelAdmin):
    list_display = (
        "internal_code",
        "specification",
        "unit_of_measure",
        "minimum_stock",
        "is_active",
    )
    search_fields = (
        "internal_code",
        "specification__name",
        "specification__material_type__name",
    )
    list_filter = (
        "unit_of_measure",
        "is_active",
    )
    autocomplete_fields = (
        "specification",
        "unit_of_measure",
    )


@admin.register(StockBatch)
class StockBatchAdmin(admin.ModelAdmin):
    list_display = (
        "stock_material",
        "lot_number",
        "unit",
        "armory",
        "initial_quantity",
        "current_quantity",
        "status",
        "expiration_date",
        "is_active",
    )
    search_fields = (
        "stock_material__internal_code",
        "stock_material__specification__name",
        "lot_number",
        "unit__name",
        "armory__name",
    )
    list_filter = (
        "status",
        "physical_condition",
        "unit",
        "armory",
        "expiration_date",
        "is_active",
    )
    autocomplete_fields = (
        "stock_material",
        "unit",
        "armory",
        "created_by",
        "updated_by",
    )
    readonly_fields = (
        "created_at",
        "updated_at",
    )


@admin.register(ComponentType)
class ComponentTypeAdmin(admin.ModelAdmin):
    list_display = (
        "name",
        "is_serialized",
        "is_active",
    )
    search_fields = (
        "name",
    )
    list_filter = (
        "is_serialized",
        "is_active",
    )


@admin.register(SerializedMaterialComponent)
class SerializedMaterialComponentAdmin(admin.ModelAdmin):
    list_display = (
        "component_type",
        "material",
        "identification_number",
        "quantity",
        "is_active",
    )
    search_fields = (
        "component_type__name",
        "material__institutional_code",
        "material__identification_number",
        "identification_number",
    )
    list_filter = (
        "component_type",
        "is_active",
    )
    autocomplete_fields = (
        "material",
        "component_type",
    )