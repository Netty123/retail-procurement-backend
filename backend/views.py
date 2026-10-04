"""
API-views для магазинов и товаров.

Здесь же PartnerUpdate — то, через что поставщик обновляет прайс.
Он принимает POST с полем url, скачивает YAML и заливает в БД.
"""
from urllib.request import urlopen
from yaml import load as load_yaml, Loader

from django.contrib.auth import authenticate
from django.core.exceptions import ValidationError
from django.core.mail import send_mail
from django.core.validators import URLValidator
from django.db import transaction
from django.http import JsonResponse
from django.urls import reverse

from django_filters.rest_framework import DjangoFilterBackend
from rest_framework import status
from rest_framework.filters import SearchFilter
from rest_framework.generics import ListAPIView, RetrieveAPIView
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework_simplejwt.tokens import RefreshToken

from backend.models import (
    Shop, Category, Product, ProductInfo,
    Parameter, ProductParameter,
    User, ConfirmEmailToken,
    Order, OrderItem,
)
from backend.serializers import (
    UserSerializer, RegisterUserSerializer, ProductInfoSerializer, BasketSerializer, OrderItemSerializer,
)

from backend.models import Order, OrderItem
from backend.serializers import BasketSerializer, OrderItemSerializer

class PartnerUpdate(APIView):
    """
    Обновление прайса от поставщика.

    Логика:
    - только авторизованный;
    - только пользователь с type='shop';
    - принимает url на YAML с прайсом;
    - сносит старый прайс магазина и заливает новый.
    """

    @transaction.atomic
    def post(self, request, *args, **kwargs):
        if not request.user.is_authenticated:
            return JsonResponse(
                {'Status': False, 'Error': 'Log in required'},
                status=403,
            )

        if request.user.type != 'shop':
            return JsonResponse(
                {'Status': False, 'Error': 'Только для магазинов'},
                status=403,
            )

        url = request.data.get('url')
        if not url:
            return JsonResponse(
                {'Status': False, 'Error': 'Не указан url'},
                status=400,
            )

        validate_url = URLValidator()
        try:
            validate_url(url)
        except ValidationError as e:
            return JsonResponse({'Status': False, 'Error': str(e)}, status=400)

        # urlopen вместо requests, чтобы не тащить зависимость ради одного вызова
        try:
            stream = urlopen(url).read()
        except Exception as e:
            return JsonResponse(
                {'Status': False, 'Error': f'Не удалось скачать файл: {e}'},
                status=400,
            )

        data = load_yaml(stream, Loader=Loader)

        shop, _ = Shop.objects.get_or_create(
            name=data['shop'],
            user_id=request.user.id,
        )

        # id категорий берём из YAML — потом на них ссылается goods[].category
        for category in data.get('categories', []):
            category_object, _ = Category.objects.get_or_create(
                id=category['id'],
                name=category['name'],
            )
            category_object.shops.add(shop.id)
            category_object.save()

        # Сносим старый прайс — ProductParameter уйдут каскадом
        ProductInfo.objects.filter(shop_id=shop.id).delete()

        for item in data.get('goods', []):
            product, _ = Product.objects.get_or_create(
                name=item['name'],
                category_id=item['category'],
            )

            product_info = ProductInfo.objects.create(
                product_id=product.id,
                external_id=item['id'],
                model=item['model'],
                price=item['price'],
                price_rrc=item['price_rrc'],
                quantity=item['quantity'],
                shop_id=shop.id,
            )

            # В YAML parameters — словарь {имя: значение}, не список
            for name, value in item['parameters'].items():
                parameter_object, _ = Parameter.objects.get_or_create(name=name)
                ProductParameter.objects.create(
                    product_info_id=product_info.id,
                    parameter_id=parameter_object.id,
                    value=str(value),
                )

        return JsonResponse({'Status': True})


class RegisterUserView(APIView):
    """POST /api/v1/user/register — регистрация + письмо с токеном."""

    def post(self, request, *args, **kwargs):
        if not request.data:
            return Response(
                {'Status': False, 'Errors': 'Не указаны все необходимые аргументы'},
                status=status.HTTP_400_BAD_REQUEST,
            )

        serializer = RegisterUserSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(
                {'Status': False, 'Errors': serializer.errors},
                status=status.HTTP_400_BAD_REQUEST,
            )

        user = serializer.save()

        # Токен создаётся сам — генератор внутри ConfirmEmailToken.save()
        token = ConfirmEmailToken.objects.create(user=user)
        confirm_url = (
            f'{request.build_absolute_uri(reverse("backend:register-confirm"))}'
            f'?email={user.email}&token={token.key}'
        )
        send_mail(
            subject='Подтверждение регистрации',
            message=f'Привет, {user.first_name}! Твой код: {token.key}\nСсылка: {confirm_url}',
            from_email=None,
            recipient_list=[user.email],
        )

        return Response(
            {'Status': True, 'user': UserSerializer(user).data},
            status=status.HTTP_201_CREATED,
        )


class ConfirmEmailView(APIView):
    """POST /api/v1/user/register/confirm — активация по токену."""

    def post(self, request, *args, **kwargs):
        email = request.data.get('email')
        token_key = request.data.get('token')

        if not email or not token_key:
            return Response(
                {'Status': False, 'Errors': 'Не указаны email и token'},
                status=status.HTTP_400_BAD_REQUEST,
            )

        try:
            token = ConfirmEmailToken.objects.get(user__email=email, key=token_key)
        except ConfirmEmailToken.DoesNotExist:
            return Response(
                {'Status': False, 'Errors': 'Неверный токен или email'},
                status=status.HTTP_400_BAD_REQUEST,
            )

        user = token.user
        user.is_active = True
        user.save()
        token.delete()

        return Response({'Status': True})


class LoginView(APIView):
    """POST /api/v1/user/login — возвращает пару JWT."""

    def post(self, request, *args, **kwargs):
        email = request.data.get('email')
        password = request.data.get('password')

        if not email or not password:
            return Response(
                {'Status': False, 'Errors': 'Не указаны email и password'},
                status=status.HTTP_400_BAD_REQUEST,
            )

        user = authenticate(request, email=email, password=password)
        if user is None:
            return Response(
                {'Status': False, 'Errors': 'Неверный email или пароль'},
                status=status.HTTP_401_UNAUTHORIZED,
            )

        # Без этой проверки неактивированный юзер получил бы токен
        if not user.is_active:
            return Response(
                {'Status': False, 'Errors': 'Email не подтверждён'},
                status=status.HTTP_401_UNAUTHORIZED,
            )

        refresh = RefreshToken.for_user(user)
        return Response({
            'Status': True,
            'access': str(refresh.access_token),
            'refresh': str(refresh),
        })


class UserDetailsView(APIView):
    """GET /api/v1/user/details — данные текущего пользователя."""

    permission_classes = [IsAuthenticated]

    def get(self, request, *args, **kwargs):
        return Response(UserSerializer(request.user).data)


class ProductInfoView(ListAPIView):
    """
    GET /api/v1/products
    Фильтры: shop, category, search (по имени товара).
    Каталог открыт без авторизации.
    """

    queryset = ProductInfo.objects.select_related(
        'product', 'product__category', 'shop',
    ).prefetch_related('product_parameters__parameter')
    serializer_class = ProductInfoSerializer
    filter_backends = [DjangoFilterBackend, SearchFilter]
    filterset_fields = ['shop']
    search_fields = ['product__name']

    def get_queryset(self):
        queryset = super().get_queryset()
        category_id = self.request.query_params.get('category')
        if category_id:
            queryset = queryset.filter(product__category_id=category_id)
        return queryset


class ProductInfoDetailView(RetrieveAPIView):
    """GET /api/v1/products/{id} — детали одного предложения."""

    queryset = ProductInfo.objects.select_related(
        'product', 'product__category', 'shop',
    ).prefetch_related('product_parameters__parameter')
    serializer_class = ProductInfoSerializer




class BasketView(APIView):
    """
    Корзина пользователя. Только для авторизованных.

    GET     — содержимое корзины
    POST    — добавить товар (product_info_id, quantity)
    PUT     — изменить количество (id позиции, quantity)
    DELETE  — удалить позицию (id)
    """

    permission_classes = [IsAuthenticated]

    def get(self, request, *args, **kwargs):
        # Корзина есть не у всех — у кого ещё нет, отдаём пустую
        basket, _ = Order.objects.get_or_create(
            user=request.user,
            state='basket',
        )
        serializer = BasketSerializer(basket)
        return Response(serializer.data)

    def post(self, request, *args, **kwargs):
        items = request.data.get('items', [])
        if not items:
            return Response(
                {'Status': False, 'Errors': 'Не передан список items'},
                status=status.HTTP_400_BAD_REQUEST,
            )

        basket, _ = Order.objects.get_or_create(
            user=request.user,
            state='basket',
        )

        created = []
        for item in items:
            product_info_id = item.get('product_info_id')
            quantity = item.get('quantity', 1)

            if not product_info_id:
                continue

            # Если позиция уже есть — увеличиваем количество, не создаём дубль
            order_item, _ = OrderItem.objects.get_or_create(
                order=basket,
                product_info_id=product_info_id,
                defaults={'quantity': quantity},
            )
            if not _:
                order_item.quantity += quantity
                order_item.save()

            created.append(order_item.id)

        return Response({'Status': True, 'items': created})

    def put(self, request, *args, **kwargs):
        item_id = request.data.get('id')
        quantity = request.data.get('quantity')

        if not item_id or quantity is None:
            return Response(
                {'Status': False, 'Errors': 'Нужны id и quantity'},
                status=status.HTTP_400_BAD_REQUEST,
            )

        try:
            item = OrderItem.objects.get(
                id=item_id,
                order__user=request.user,
                order__state='basket',
            )
        except OrderItem.DoesNotExist:
            return Response(
                {'Status': False, 'Errors': 'Позиция не найдена'},
                status=status.HTTP_404_NOT_FOUND,
            )

        item.quantity = quantity
        item.save()
        return Response({'Status': True})

    def delete(self, request, *args, **kwargs):
        item_id = request.data.get('id')
        if not item_id:
            return Response(
                {'Status': False, 'Errors': 'Не указан id'},
                status=status.HTTP_400_BAD_REQUEST,
            )

        deleted, _ = OrderItem.objects.filter(
            id=item_id,
            order__user=request.user,
            order__state='basket',
        ).delete()

        if not deleted:
            return Response(
                {'Status': False, 'Errors': 'Позиция не найдена'},
                status=status.HTTP_404_NOT_FOUND,
            )

        return Response({'Status': True})