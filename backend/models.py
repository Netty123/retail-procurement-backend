from django.contrib.auth.models import AbstractUser, BaseUserManager
from django.db import models
from django.utils.translation import gettext_lazy as _


class UserManager(BaseUserManager):
    """Менеджер для кастомного пользователя с email вместо username."""

    use_in_migrations = True

    def _create_user(self, email, password, **extra_fields):
        if not email:
            raise ValueError('Email обязателен')
        email = self.normalize_email(email)
        user = self.model(email=email, **extra_fields)
        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_user(self, email, password=None, **extra_fields):
        extra_fields.setdefault('is_staff', False)
        extra_fields.setdefault('is_superuser', False)
        return self._create_user(email, password, **extra_fields)

    def create_superuser(self, email, password, **extra_fields):
        extra_fields.setdefault('is_staff', True)
        extra_fields.setdefault('is_superuser', True)
        extra_fields.setdefault('is_active', True)

        if extra_fields.get('is_staff') is not True:
            raise ValueError('Суперпользователь должен иметь is_staff=True')
        if extra_fields.get('is_superuser') is not True:
            raise ValueError('Суперпользователь должен иметь is_superuser=True')

        return self._create_user(email, password, **extra_fields)


class User(AbstractUser):
    """Кастомный пользователь. Логин — по email."""

    USER_TYPE_CHOICES = (
        ('buyer', 'Покупатель'),
        ('shop', 'Магазин'),
    )

    username = None
    email = models.EmailField(_('email address'), unique=True)
    first_name = models.CharField(_('first name'), max_length=50, blank=True)
    last_name = models.CharField(_('last name'), max_length=50, blank=True)
    middle_name = models.CharField(_('middle name'), max_length=50, blank=True)
    company = models.CharField(_('company'), max_length=100, blank=True)
    position = models.CharField(_('position'), max_length=100, blank=True)
    type = models.CharField(_('user type'), max_length=10, choices=USER_TYPE_CHOICES, default='buyer')
    is_active = models.BooleanField(default=False)

    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS = []

    objects = UserManager()

    class Meta:
        verbose_name = 'Пользователь'
        verbose_name_plural = 'Пользователи'

    def __str__(self):
        return self.email



class Shop(models.Model):
    """Магазин / поставщик."""

    name = models.CharField(max_length=100, verbose_name='Название')
    url = models.URLField(null=True, blank=True, verbose_name='Ссылка')
    user = models.OneToOneField(
        User,
        verbose_name='Пользователь',
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name='shop',
    )
    state = models.BooleanField(default=True, verbose_name='Приём заказов')

    class Meta:
        verbose_name = 'Магазин'
        verbose_name_plural = 'Магазины'
        ordering = ['name']

    def __str__(self):
        return self.name



class Category(models.Model):
    """Категория товара. Поддерживает вложенность."""

    name = models.CharField(max_length=100, verbose_name='Название')
    shops = models.ManyToManyField(
        Shop,
        related_name='categories',
        blank=True,
        verbose_name='Магазины',
    )
    parent = models.ForeignKey(
        'self',
        verbose_name='Родительская категория',
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name='children',
    )

    class Meta:
        verbose_name = 'Категория'
        verbose_name_plural = 'Категории'
        ordering = ['name']

    def __str__(self):
        return self.name


class Product(models.Model):
    """Товар."""

    name = models.CharField(max_length=150, verbose_name='Название')
    category = models.ForeignKey(
        Category,
        verbose_name='Категория',
        on_delete=models.CASCADE,
        related_name='products',
    )

    class Meta:
        verbose_name = 'Товар'
        verbose_name_plural = 'Товары'
        ordering = ['name']

    def __str__(self):
        return self.name



class Parameter(models.Model):
    """Название характеристики (например, «Цвет», «Вес»)."""

    name = models.CharField(max_length=100, unique=True, verbose_name='Название')

    class Meta:
        verbose_name = 'Параметр'
        verbose_name_plural = 'Параметры'
        ordering = ['name']

    def __str__(self):
        return self.name


class ProductInfo(models.Model):
    """Конкретное предложение товара от магазина."""

    class Meta:
        verbose_name = 'Информация о товаре'
        verbose_name_plural = 'Информация о товарах'
        unique_together = (('product', 'shop', 'external_id'),)

    product = models.ForeignKey(
        Product,
        verbose_name='Товар',
        on_delete=models.CASCADE,
        related_name='product_infos',
    )
    shop = models.ForeignKey(
        Shop,
        verbose_name='Магазин',
        on_delete=models.CASCADE,
        related_name='product_infos',
    )
    external_id = models.PositiveIntegerField(verbose_name='Внешний ID')
    model = models.CharField(max_length=100, verbose_name='Модель', blank=True)
    quantity = models.PositiveIntegerField(verbose_name='Количество')
    price = models.DecimalField(max_digits=10, decimal_places=2, verbose_name='Цена')
    price_rrc = models.DecimalField(max_digits=10, decimal_places=2, verbose_name='Рекомендованная цена')
    parameters = models.ManyToManyField(
        Parameter,
        through='ProductParameter',
        related_name='product_infos',
        verbose_name='Характеристики',
    )

    def __str__(self):
        return f'{self.product.name} — {self.shop.name}'


class ProductParameter(models.Model):
    """Значение характеристики для конкретного предложения."""

    product_info = models.ForeignKey(
        ProductInfo,
        verbose_name='Информация о товаре',
        on_delete=models.CASCADE,
        related_name='product_parameters',
    )
    parameter = models.ForeignKey(
        Parameter,
        verbose_name='Параметр',
        on_delete=models.CASCADE,
        related_name='product_parameters',
    )
    value = models.CharField(max_length=255, verbose_name='Значение')

    class Meta:
        verbose_name = 'Значение параметра'
        verbose_name_plural = 'Значения параметров'
        unique_together = (('product_info', 'parameter'),)

    def __str__(self):
        return f'{self.parameter.name}: {self.value}'



class Contact(models.Model):
    """Адрес доставки пользователя."""

    user = models.ForeignKey(
        User,
        verbose_name='Пользователь',
        on_delete=models.CASCADE,
        related_name='contacts',
    )
    city = models.CharField(max_length=50, verbose_name='Город')
    street = models.CharField(max_length=100, verbose_name='Улица')
    house = models.CharField(max_length=15, verbose_name='Дом')
    structure = models.CharField(max_length=15, verbose_name='Корпус', blank=True)
    building = models.CharField(max_length=15, verbose_name='Строение', blank=True)
    apartment = models.CharField(max_length=15, verbose_name='Квартира', blank=True)
    phone = models.CharField(max_length=20, verbose_name='Телефон')

    class Meta:
        verbose_name = 'Контакты пользователя'
        verbose_name_plural = 'Список контактов пользователя'

    def __str__(self):
        return f'{self.city}, {self.street}, {self.house}'


class ConfirmEmailToken(models.Model):
    """Токен подтверждения email."""

    user = models.ForeignKey(
        User,
        verbose_name='Пользователь',
        on_delete=models.CASCADE,
        related_name='confirm_email_tokens',
    )
    key = models.CharField(max_length=64, unique=True, verbose_name='Ключ')
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='Создан')

    class Meta:
        verbose_name = 'Токен подтверждения email'
        verbose_name_plural = 'Токены подтверждения email'

    def __str__(self):
        return f'Токен для {self.user.email}'
# Create your models here.
