"""
Management-команда для загрузки прайса из YAML-файла.
Используется для локальной отладки и разовой загрузки.
В проде то же самое делает API-view PartnerUpdate (см. backend/views.py).
"""
import yaml
from django.core.management.base import BaseCommand
from django.db import transaction

from backend.models import (
    Shop, Category, Product, ProductInfo,
    Parameter, ProductParameter,
)


class Command(BaseCommand):
    help = 'Импорт товаров из YAML-файла (структура как в shop1.yaml)'

    def add_arguments(self, parser):
        parser.add_argument('file', type=str, help='Путь к YAML-файлу')

    @transaction.atomic
    def handle(self, *args, **options):
        file_path = options['file']
        self.stdout.write(f'Импорт из {file_path}...')

        # Читаем YAML. encoding utf-8 - на случай русских букв в названиях
        with open(file_path, 'r', encoding='utf-8') as f:
            data = yaml.safe_load(f)

        # 1. Магазин. get_or_create, чтобы повторный импорт не падал
        shop_name = data.get('shop')
        if not shop_name:
            self.stderr.write('В YAML нет поля shop — нечего импортировать')
            return

        shop, _ = Shop.objects.get_or_create(name=shop_name)
        self.stdout.write(f'Магазин: {shop.name}')

        # 2. Категории. По методичке id категории берём прямо из YAML,
        # чтобы потом связать с товаром через поле category в goods.
        for category_data in data.get('categories', []):
            category, _ = Category.objects.get_or_create(
                id=category_data['id'],
                defaults={'name': category_data['name']},
            )
            category.shops.add(shop)
            self.stdout.write(f'  Категория: {category.name}')

        # 3. Перед заливкой удаляем старый прайс этого магазина.
        # Иначе при повторном импорте будут дубли ProductInfo.
        # ProductParameter уйдут каскадом, потому что FK на ProductInfo.
        ProductInfo.objects.filter(shop=shop).delete()
        self.stdout.write('  Старый прайс удалён')

        # 4. Товары
        for item in data.get('goods', []):
            # get_or_create по имени и категории - если товар уже есть, переиспользуем
            product, _ = Product.objects.get_or_create(
                name=item['name'],
                category_id=item['category'],
            )

            # Создаём ProductInfo - конкретное предложение от этого магазина
            product_info = ProductInfo.objects.create(
                product=product,
                shop=shop,
                external_id=item['id'],
                model=item['model'],
                price=item['price'],
                price_rrc=item['price_rrc'],
                quantity=item['quantity'],
            )

            # 5. Параметры - это словарь {имя: значение}
            for param_name, param_value in item.get('parameters', {}).items():
                parameter, _ = Parameter.objects.get_or_create(name=param_name)
                ProductParameter.objects.create(
                    product_info=product_info,
                    parameter=parameter,
                    value=str(param_value),
                )

            self.stdout.write(f'    Товар: {product.name}')

        self.stdout.write(self.style.SUCCESS('Импорт завершён'))