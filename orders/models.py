from django.db import models
from django.utils.translation import gettext_lazy as _

from backend.models import User, Contact, ProductInfo


class Order(models.Model):
    """Заказ пользователя. Корзина — это Order со статусом 'basket'."""

    class STATUS_CHOICES(models.TextChoices):
        BASKET = 'basket', 'Корзина'
        NEW = 'new', 'Новый'
        CONFIRMED = 'confirmed', 'Подтверждён'
        ASSEMBLED = 'assembled', 'Собран'
        SENT = 'sent', 'Отправлен'
        DELIVERED = 'delivered', 'Доставлен'
        CANCELED = 'canceled', 'Отменён'

    user = models.ForeignKey(
        User,
        verbose_name='Пользователь',
        on_delete=models.CASCADE,
        related_name='orders',
    )
    dt = models.DateTimeField(auto_now_add=True, verbose_name='Дата создания')
    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES.choices,
        default=STATUS_CHOICES.BASKET,
        verbose_name='Статус',
    )
    contact = models.ForeignKey(
        Contact,
        verbose_name='Контакт',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='orders',
    )

    class Meta:
        verbose_name = 'Заказ'
        verbose_name_plural = 'Заказы'
        ordering = ['-dt']

    def __str__(self):
        return f'Заказ №{self.id} от {self.user.email} ({self.get_status_display()})'

    @property
    def total_sum(self):
        """Общая стоимость заказа."""
        return sum(item.sum for item in self.ordered_items.all())

    @property
    def total_quantity(self):
        """Общее количество позиций в заказе."""
        return sum(item.quantity for item in self.ordered_items.all())


class OrderItem(models.Model):
    """Позиция заказа: конкретный ProductInfo + количество."""

    order = models.ForeignKey(
        Order,
        verbose_name='Заказ',
        on_delete=models.CASCADE,
        related_name='ordered_items',
    )
    product_info = models.ForeignKey(
        ProductInfo,
        verbose_name='Информация о товаре',
        on_delete=models.CASCADE,
        related_name='order_items',
    )
    quantity = models.PositiveIntegerField(verbose_name='Количество', default=1)

    class Meta:
        verbose_name = 'Позиция заказа'
        verbose_name_plural = 'Позиции заказов'
        unique_together = (('order', 'product_info'),)

    def __str__(self):
        return f'{self.product_info.product.name} × {self.quantity}'

    @property
    def sum(self):
        """Стоимость позиции."""
        return self.product_info.price * self.quantity
# Create your models here.
