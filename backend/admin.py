from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from .models import (
    User, Shop, Category, Product, ProductInfo,
    Parameter, ProductParameter, Contact,
    Order, OrderItem, ConfirmEmailToken,
)


@admin.register(User)
class CustomUserAdmin(UserAdmin):
    model = User
    list_display = ('email', 'username', 'first_name', 'last_name', 'type', 'is_active', 'is_staff')
    list_filter = ('type', 'is_active', 'is_staff')
    search_fields = ('email', 'username', 'first_name', 'last_name')
    ordering = ('email',)


@admin.register(Shop)
class ShopAdmin(admin.ModelAdmin):
    list_display = ('name', 'url', 'state')
    list_filter = ('state',)
    search_fields = ('name',)


@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display = ('name',)
    search_fields = ('name',)


@admin.register(Product)
class ProductAdmin(admin.ModelAdmin):
    list_display = ('name', 'category')
    list_filter = ('category',)
    search_fields = ('name',)


@admin.register(Parameter)
class ParameterAdmin(admin.ModelAdmin):
    list_display = ('name',)


@admin.register(ProductInfo)
class ProductInfoAdmin(admin.ModelAdmin):
    list_display = ('product', 'shop', 'price', 'quantity', 'external_id')
    list_filter = ('shop',)
    search_fields = ('product__name', 'external_id')


@admin.register(ProductParameter)
class ProductParameterAdmin(admin.ModelAdmin):
    list_display = ('product_info', 'parameter', 'value')


@admin.register(Contact)
class ContactAdmin(admin.ModelAdmin):
    list_display = ('user', 'city', 'street', 'house', 'phone')


@admin.register(Order)
class OrderAdmin(admin.ModelAdmin):
    list_display = ('id', 'user', 'state', 'dt', 'contact')
    list_filter = ('state', 'dt')
    search_fields = ('user__email',)


@admin.register(OrderItem)
class OrderItemAdmin(admin.ModelAdmin):
    list_display = ('order', 'product_info', 'quantity')
    search_fields = ('order__id', 'product_info__product__name')


@admin.register(ConfirmEmailToken)
class ConfirmEmailTokenAdmin(admin.ModelAdmin):
    list_display = ('user', 'key', 'created_at')