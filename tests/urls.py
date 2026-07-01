"""
URLconf used only by the test suite — NotifyFork doesn't ship its own
urls.py. A host project wires it in with:
    path("api/v1/", include("notifyfork.api.urls"))
"""
from django.urls import path, include

urlpatterns = [
    path("api/v1/", include("notifyfork.api.urls")),
]
