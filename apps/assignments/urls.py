from rest_framework.routers import DefaultRouter

from .views import IndividualAssignmentViewSet


app_name = "assignments"


router = DefaultRouter()

router.register(
    "",
    IndividualAssignmentViewSet,
    basename="individual-assignment",
)


urlpatterns = router.urls