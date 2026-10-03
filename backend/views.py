"""
API-views для магазинов и товаров.

Здесь же PartnerUpdate — то, через что поставщик обновляет прайс.
Он принимает POST с полем url, скачивает YAML и заливает в БД.
"""
from urllib.request import urlopen
from yaml import load as load_yaml, Loader

from django.core.exceptions import ValidationError
from django.core.validators import URLValidator
from django.db import transaction
from django.http import JsonResponse
from rest_framework.views import APIView

from backend.models import (
    Shop, Category, Product, ProductInfo,
    Parameter, ProductParameter,
)


class PartnerUpdate(APIView):
    """
    Обновление прайса от поставщика.

    Логика:
    - только авторизованный;
    - только пользователь с type='shop';
    - принимает url на YAML с прайсом;
    - сносит старый прайс магазина и заливает новый.

    Всё в одной транзакции: если что-то упадёт в середине, БД не останется
    в половинчатом состоянии.
    """

    @transaction.atomic
    def post(self, request, *args, **kwargs):
        # 1. Проверка авторизации
        if not request.user.is_authenticated:
            return JsonResponse(
                {'Status': False, 'Error': 'Log in required'},
                status=403,
            )

        # 2. Только магазины могут обновлять прайс
        if request.user.type != 'shop':
            return JsonResponse(
                {'Status': False, 'Error': 'Только для магазинов'},
                status=403,
            )

        # 3. URL обязателен
        url = request.data.get('url')
        if not url:
            return JsonResponse(
                {'Status': False, 'Error': 'Не указан url'},
                status=400,
            )

        # 4. Проверяем, что url вообще похож на url
        validate_url = URLValidator()
        try:
            validate_url(url)
        except ValidationError as e:
            return JsonResponse({'Status': False, 'Error': str(e)}, status=400)

        # 5. Скачиваем YAML. Использую urlopen, чтобы не тащить requests ради одного вызова
        try:
            stream = urlopen(url).read()
        except Exception as e:
            return JsonResponse(
                {'Status': False, 'Error': f'Не удалось скачать файл: {e}'},
                status=400,
            )

        data = load_yaml(stream, Loader=Loader)

        # 6. Магазин привязываем к текущему пользователю.
        # get_or_create по name+user — если такой магазин уже есть, используем его
        shop, _ = Shop.objects.get_or_create(
            name=data['shop'],
            user_id=request.user.id,
        )

        # 7. Категории. id берём из YAML — это же id потом используется в goods.category
        for category in data.get('categories', []):
            category_object, _ = Category.objects.get_or_create(
                id=category['id'],
                name=category['name'],
            )
            category_object.shops.add(shop.id)
            category_object.save()

        # 8. Перед заливкой нового прайса сносим старый.
        # ProductParameter уйдут каскадом — у них FK на ProductInfo
        ProductInfo.objects.filter(shop_id=shop.id).delete()

        # 9. Товары
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

            # 10. Параметры в YAML — это словарь {имя: значение}, не список
            for name, value in item['parameters'].items():
                parameter_object, _ = Parameter.objects.get_or_create(name=name)
                ProductParameter.objects.create(
                    product_info_id=product_info.id,
                    parameter_id=parameter_object.id,
                    value=str(value),
                )

        return JsonResponse({'Status': True})