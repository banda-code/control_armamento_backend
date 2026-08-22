from django.urls import path

from .views import (
    ArmamentDetailExportView,
    ArmamentDetailPreviewView,
    ArmamentReportOptionsView,
    GeneralMaterialExportView,
    GeneralMaterialPreviewView,
    IndividualFiliationExportView,
    IndividualFiliationConfigView,
)


app_name = "reports"


urlpatterns = [
    path(
        "armament/options/",
        ArmamentReportOptionsView.as_view(),
        name="armament-options",
    ),
    path(
        "armament/preview/",
        ArmamentDetailPreviewView.as_view(),
        name="armament-preview",
    ),
    path(
        "armament/export/",
        ArmamentDetailExportView.as_view(),
        name="armament-export",
    ),
    path(
        "general/preview/",
        GeneralMaterialPreviewView.as_view(),
        name="general-preview",
    ),
    path(
        "general/export/",
        GeneralMaterialExportView.as_view(),
        name="general-export",
    ),
    path(
        "individual-filiation/export/",
        IndividualFiliationExportView.as_view(),
        name="individual-filiation-export",
    ),
    path(
        "individual-filiation/config/",
        IndividualFiliationConfigView.as_view(),
        name="individual-filiation-config",
    ),
]
