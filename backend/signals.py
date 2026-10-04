from django.core.mail import EmailMultiAlternatives
from django.dispatch import receiver
from django.urls import reverse
from django_rest_passwordreset.signals import reset_password_token_created

from backend.models import User


@receiver(reset_password_token_created)
def password_reset_token_created(sender, instance, reset_password_token, *args, **kwargs):
    """
    Ловим момент, когда django-rest-passwordreset сгенерировал токен,
    и отправляем письмо со ссылкой на сброс пароля.
    """
    # Пытаемся взять имя пользователя - если пусто, подставляем email
    user = User.objects.get(email=reset_password_token.user.email)
    greeting = f'{user.first_name} {user.last_name}'.strip() or user.email

    # Ссылку на фронт здесь собираем «на глазок» - реального фронта у нас нет,
    # поэтому кладём и токен, и email прямо в письмо, чтобы можно было скопировать
    subject = 'Сброс пароля'
    text = (
        f'Здравствуйте, {greeting}!\n\n'
        f'Код для сброса пароля: {reset_password_token.key}\n'
        f'Email: {reset_password_token.user.email}\n\n'
        f'Если вы не запрашивали сброс — просто проигнорируйте это письмо.'
    )

    msg = EmailMultiAlternatives(
        subject,
        text,
        from_email=None,
        to=[reset_password_token.user.email],
    )
    msg.send()