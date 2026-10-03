from rest_framework import serializers

from backend.models import User


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