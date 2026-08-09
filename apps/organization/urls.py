from rest_framework.routers import DefaultRouter

from .views import (
    InstitutionViewSet,
    PositionViewSet,
    RankViewSet,
    SectionViewSet,
    UnitViewSet,
)


router = DefaultRouter()
router.register("institutions", InstitutionViewSet, basename="institution")
router.register("units", UnitViewSet, basename="unit")
router.register("ranks", RankViewSet, basename="rank")
router.register("positions", PositionViewSet, basename="position")
router.register("sections", SectionViewSet, basename="section")

urlpatterns = router.urls
