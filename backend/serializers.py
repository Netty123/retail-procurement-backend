from rest_framework import serializers
from backend.models import User
from backend.models import User, Category, Product, ProductInfo, Parameter, ProductParameter, Order, OrderItem, Contact

class UserSerializer(serializers.ModelSerializer):
    """Отдаёт данные пользователя. Пароль не включён."""

    class Meta:
        model = User
        fields = (
            'id', 'email', 'username',
            'first_name', 'last_name',
            'company', 'position', 'type',
        )


class RegisterUserSerializer(serializers.ModelSerializer):
    """Регистрация. password — write_only, чтобы не возвращался в ответе."""

    password = serializers.CharField(write_only=True, min_length=8)

    class Meta:
        model = User
        fields = (
            'id', 'email', 'username',
            'first_name', 'last_name',
            'password',
        )

    def create(self, validated_data):
        # create_user сам хеширует пароль и ставит is_active=False
        return User.objects.create_user(**validated_data)






class CategorySerializer(serializers.ModelSerializer):
    class Meta:
        model = Category
        fields = ('id', 'name')


class ParameterSerializer(serializers.ModelSerializer):
    class Meta:
        model = Parameter
        fields = ('id', 'name')


class ProductSerializer(serializers.ModelSerializer):
    category = CategorySerializer(read_only=True)

    class Meta:
        model = Product
        fields = ('id', 'name', 'category')


class ProductParameterSerializer(serializers.ModelSerializer):
    parameter = serializers.CharField(source='parameter.name')

    class Meta:
        model = ProductParameter
        fields = ('parameter', 'value')


class ProductInfoSerializer(serializers.ModelSerializer):
    # Достаём связанные объекты одним запросом
    product = ProductSerializer(read_only=True)
    shop = serializers.CharField(source='shop.name')
    parameters = ProductParameterSerializer(
        source='product_parameters', many=True, read_only=True,
    )

    class Meta:
        model = ProductInfo
        fields = (
            'id', 'product', 'shop',
            'quantity', 'price', 'price_rrc',
            'parameters',
        )



class OrderItemSerializer(serializers.ModelSerializer):
    # ProductInfo отдаём вложенно — фронту нужны цена, название, магазин
    product_info = ProductInfoSerializer(read_only=True)
    product_info_id = serializers.IntegerField(write_only=True)
    sum = serializers.SerializerMethodField()

    class Meta:
        model = OrderItem
        fields = ('id', 'product_info', 'product_info_id', 'quantity', 'sum')

    def get_sum(self, obj):
        # Цена * количество — просто чтобы клиенту не считать самому
        return obj.product_info.price * obj.quantity


class BasketSerializer(serializers.ModelSerializer):
    items = OrderItemSerializer(source='ordered_items', many=True, read_only=True)

    class Meta:
        model = Order
        fields = ('id', 'state', 'items')


class ContactSerializer(serializers.ModelSerializer):
    class Meta:
        model = Contact
        fields = (
            'id', 'city', 'street', 'house',
            'structure', 'building', 'apartment', 'phone',
        )
        # user подставим во view — клиент его не передаёт
        read_only_fields = ('id',)


class OrderSerializer(serializers.ModelSerializer):
    # items — это позиции заказа, уже сериализованные OrderItemSerializer
    items = OrderItemSerializer(source='ordered_items', many=True, read_only=True)
    total_sum = serializers.SerializerMethodField()
    contact = ContactSerializer(read_only=True)

    class Meta:
        model = Order
        fields = ('id', 'state', 'dt', 'contact', 'items', 'total_sum')

    def get_total_sum(self, obj):
        # Сумма всех позиций. Для больших заказов лучше annotate,
        # но у нас заказы небольшие — можно и в Python
        return sum(item.product_info.price * item.quantity for item in obj.ordered_items.all())