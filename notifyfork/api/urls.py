from django.urls import path, include

urlpatterns = [
    path("webhooks/", include("notifyfork.api.webhooks.urls")),
]
