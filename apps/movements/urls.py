from rest_framework.routers import DefaultRouter

from .views import SerializedMovementViewSet


app_name = "movements"


router = DefaultRouter()

router.register(
    "",
    SerializedMovementViewSet,
    basename="serialized-movement",
)


urlpatterns = router.urls