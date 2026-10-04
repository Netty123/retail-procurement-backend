from django.contrib import admin
from django.urls import path, include

urlpatterns = [
    path('admin/', admin.site.urls),
    path('api/v1/', include('backend.urls')),

    path(
    'api/v1/user/password_reset/',
    include('django_rest_passwordreset.urls', namespace='password_reset'),
),
]