from django.urls import include, path
from rest_framework.routers import (
    DefaultRouter,
)

from apps.inventory.views import (
    ArmoryViewSet,
    CaliberViewSet,
    ComponentTypeViewSet,
    CountryViewSet,
    ManufacturerViewSet,
    MaterialCategoryViewSet,
    MaterialSpecificationViewSet,
    MaterialTypeViewSet,
    SerializedMaterialComponentViewSet,
    SerializedMaterialViewSet,
    StockBatchViewSet,
    StockMaterialViewSet,
    UnitOfMeasureViewSet,
)


app_name = "inventory"


router = DefaultRouter()


router.register(
    "categories",
    MaterialCategoryViewSet,
    basename="material-category",
)

router.register(
    "material-types",
    MaterialTypeViewSet,
    basename="material-type",
)

router.register(
    "manufacturers",
    ManufacturerViewSet,
    basename="manufacturer",
)

router.register(
    "countries",
    CountryViewSet,
    basename="country",
)

router.register(
    "calibers",
    CaliberViewSet,
    basename="caliber",
)

router.register(
    "units-of-measure",
    UnitOfMeasureViewSet,
    basename="unit-of-measure",
)

router.register(
    "specifications",
    MaterialSpecificationViewSet,
    basename="material-specification",
)

router.register(
    "armories",
    ArmoryViewSet,
    basename="armory",
)

router.register(
    "serialized-materials",
    SerializedMaterialViewSet,
    basename="serialized-material",
)

router.register(
    "stock-materials",
    StockMaterialViewSet,
    basename="stock-material",
)

router.register(
    "stock-batches",
    StockBatchViewSet,
    basename="stock-batch",
)

router.register(
    "component-types",
    ComponentTypeViewSet,
    basename="component-type",
)

router.register(
    "components",
    SerializedMaterialComponentViewSet,
    basename="material-component",
)


urlpatterns = [
    path(
        "",
        include(router.urls),
    ),
]