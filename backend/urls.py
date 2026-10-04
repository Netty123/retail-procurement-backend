from django.urls import path

from backend.views import (
    PartnerUpdate,
    RegisterUserView,
    ConfirmEmailView,
    LoginView,
    UserDetailsView,
    ProductInfoView,
    ProductInfoDetailView,
)

app_name = 'backend'

urlpatterns = [
    path('partner/update', PartnerUpdate.as_view(), name='partner-update'),

    path('user/register', RegisterUserView.as_view(), name='user-register'),
    path('user/register/confirm', ConfirmEmailView.as_view(), name='register-confirm'),
    path('user/login', LoginView.as_view(), name='user-login'),
    path('user/details', UserDetailsView.as_view(), name='user-details'),

    path('products', ProductInfoView.as_view(), name='products'),
    path('products/<int:pk>', ProductInfoDetailView.as_view(), name='product-detail'),
]