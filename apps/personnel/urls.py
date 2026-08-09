from rest_framework.routers import DefaultRouter

from .views import PersonnelViewSet


app_name = "personnel"


router = DefaultRouter()

router.register(
    "",
    PersonnelViewSet,
    basename="personnel",
)


urlpatterns = router.urls