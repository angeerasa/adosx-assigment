from django.contrib import admin
from django.urls import path, include

import recon.urls

urlpatterns = [
    path('admin/', admin.site.urls),
    path("api/", include(recon.urls))
]
