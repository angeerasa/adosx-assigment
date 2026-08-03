from django.contrib import admin
from django.urls import path, include
from django.views.generic import TemplateView

import recon.urls

urlpatterns = [
    path('admin/', admin.site.urls),
    path("api/", include(recon.urls)),

    path('', TemplateView.as_view(template_name='index.html'), name="index"),
]
