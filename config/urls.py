from django.contrib import admin
from django.urls import path, include

urlpatterns = [
    path('admin/', admin.site.urls),
    # API v1 — сюда будет расти всё остальное (auth, products, basket, orders)
    path('api/v1/', include('backend.urls')),
]