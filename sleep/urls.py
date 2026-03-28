from django.urls import path

from .views import (
    add_sleep_record_view,
    import_history_view,
    import_sleep_data_view,
    sleep_detail_view,
    sleep_list_view,
)

urlpatterns = [
    path("sen/import/", import_sleep_data_view, name="sleep_import"),
    path("sen/dodaj/", add_sleep_record_view, name="sleep_add"),
    path("sen/importy/", import_history_view, name="sleep_import_history"),
    path("sen/noce/", sleep_list_view, name="sleep_list"),
    path("sen/noce/<int:pk>/", sleep_detail_view, name="sleep_detail"),
]
