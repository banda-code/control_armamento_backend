from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.urls import include, path

from config.views import health_check
from django.views.generic import RedirectView

from drf_spectacular.views import (
    SpectacularAPIView,
    SpectacularRedocView,
    SpectacularSwaggerView,
)

urlpatterns = [
    path("api/docs/", SpectacularSwaggerView.as_view(url_name="schema"), name="swagger-ui"),
    path("api/auth/", RedirectView.as_view(url="/api/docs/",permanent=False,), name="auth-docs",),
    path("api/schema/", SpectacularAPIView.as_view(), name="schema"),
    path("api/redoc/", SpectacularRedocView.as_view(url_name="schema"), name="redoc"),
    path("admin/", admin.site.urls),
    path("api/health/", health_check, name="health-check"),
    path("api/", include("apps.accounts.urls")),
    path("api/organization/", include("apps.organization.urls")),
    path("api/audit/", include("apps.audit.urls")),
    path("api/inventory/",include("apps.inventory.urls"),),
    path("api/personnel/", include("apps.personnel.urls")),
    path("api/assignments/", include("apps.assignments.urls")),
]
if settings.DEBUG:
    urlpatterns += static(
        settings.MEDIA_URL,
        document_root=settings.MEDIA_ROOT,
    )