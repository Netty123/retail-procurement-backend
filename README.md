# Backend для автоматизации закупок в розничной сети

Дипломный проект профессии «Python-разработчик: расширенный курс» (Нетология).

REST API для сервиса заказа товаров: клиенты делают закупки по каталогу от нескольких поставщиков, поставщики обновляют прайс, администратор получает накладные.

---

## Стек

- **Python 3.10**
- **Django 5.2** + **Django REST Framework**
- **PostgreSQL** — база данных
- **Redis** — брокер для Celery (для будущих асинхронных задач)
- **JWT** (`djangorestframework-simplejwt`) — авторизация
- **django-filter** — фильтрация в API
- **drf-spectacular** — OpenAPI / Swagger-документация
- **django-rest-passwordreset** — восстановление пароля
- **PyYAML** — парсинг прайсов поставщиков
- **python-dotenv** — переменные окружения

---

## Установка и запуск

### 1. Клонировать репозиторий

```bash
git clone https://github.com/Netty123/retail-procurement-backend.git
cd retail-procurement-backend
```

### 2. Создать виртуальное окружение

```bash
python3 -m venv venv
source venv/bin/activate
```

### 3. Установить зависимости

```bash
pip install --upgrade pip
pip install -r requirements.txt
```

### 4. Подготовить переменные окружения

Скопируй шаблон и заполни реальными данными:

```bash
cp .env.example .env
```

Содержимое `.env`:

```
SECRET_KEY=любая-длинная-случайная-строка
DEBUG=True

DB_NAME=retail_db
DB_USER=netty
DB_PASSWORD=твой_пароль
DB_HOST=localhost
DB_PORT=5432

EMAIL_HOST=smtp.yandex.ru
EMAIL_PORT=465
EMAIL_HOST_USER=твоя_почта@yandex.ru
EMAIL_HOST_PASSWORD=пароль_приложения
EMAIL_USE_SSL=True

CELERY_BROKER_URL=redis://localhost:6379/0
CELERY_RESULT_BACKEND=redis://localhost:6379/0
```

### 5. Создать базу в PostgreSQL

```bash
sudo -u postgres psql
```

В консоли:

```sql
CREATE USER netty WITH PASSWORD 'твой_пароль';
CREATE DATABASE retail_db OWNER netty;
ALTER USER netty CREATEDB;
GRANT ALL PRIVILEGES ON DATABASE retail_db TO netty;
\q
```

### 6. Запустить службы

```bash
sudo service postgresql start
sudo service redis-server start
```

### 7. Применить миграции

```bash
python manage.py migrate
```

### 8. Создать суперпользователя

```bash
python manage.py createsuperuser
```

### 9. Запустить сервер

```bash
python manage.py runserver
```

API будет доступно на `http://127.0.0.1:8000/api/v1/`.

Админка: `http://127.0.0.1:8000/admin/`.

---

## Импорт товаров из YAML

Management-команда для загрузки прайса:

```bash
python manage.py import_products data/shop1.yaml
python manage.py import_products data/shop2.yaml
```

Формат YAML:

```yaml
shop: Название магазина
categories:
  - id: 224
    name: Смартфоны
goods:
  - id: 4216292
    category: 224
    model: apple/iphone/xs-max
    name: Смартфон Apple iPhone XS Max 512GB
    price: 110000
    price_rrc: 116990
    quantity: 14
    parameters:
      "Цвет": золотистый
      "Встроенная память (Гб)": 512
```

---

## API

Базовый префикс: `/api/v1/`

### Пользователи

| Метод | URL | Описание | Авторизация |
|-------|-----|----------|-------------|
| POST | `/user/register` | Регистрация (создаёт `is_active=False`, шлёт email с токеном) | нет |
| POST | `/user/register/confirm` | Подтверждение email по токену | нет |
| POST | `/user/login` | Логин, выдаёт JWT (`access` и `refresh`) | нет |
| GET | `/user/details` | Данные текущего пользователя | JWT |
| POST | `/user/password_reset/` | Запрос сброса пароля | нет |
| POST | `/user/password_reset/confirm/` | Смена пароля по токену | нет |

### Каталог

| Метод | URL | Описание | Авторизация |
|-------|-----|----------|-------------|
| GET | `/products` | Список товаров. Фильтры: `?shop=`, `?category=`, `?search=` | нет |
| GET | `/products/{id}` | Детали товара | нет |

### Корзина

| Метод | URL | Описание | Авторизация |
|-------|-----|----------|-------------|
| GET | `/basket` | Содержимое корзины | JWT |
| POST | `/basket` | Добавить товары (`items: [{product_info_id, quantity}]`) | JWT |
| PUT | `/basket` | Изменить количество (`{id, quantity}`) | JWT |
| DELETE | `/basket` | Удалить позицию (`{id}`) | JWT |

### Контакты (адреса доставки)

| Метод | URL | Описание | Авторизация |
|-------|-----|----------|-------------|
| GET | `/contacts` | Список контактов пользователя | JWT |
| POST | `/contacts` | Добавить контакт | JWT |
| PUT | `/contacts` | Изменить (`{id, ...поля}`) | JWT |
| DELETE | `/contacts` | Удалить (`{id}`) | JWT |

### Заказы

| Метод | URL | Описание | Авторизация |
|-------|-----|----------|-------------|
| GET | `/order` | Список заказов пользователя | JWT |
| POST | `/order` | Подтвердить заказ (`{contact: <id>}`) | JWT |
| GET | `/order/{id}` | Детали заказа | JWT |

### Поставщик

| Метод | URL | Описание | Авторизация |
|-------|-----|----------|-------------|
| POST | `/partner/update` | Обновить прайс по ссылке на YAML (`{url: "..."}`) | JWT (type=shop) |

---

## Пример сквозного сценария

```bash
# 1. Регистрация
curl -X POST http://127.0.0.1:8000/api/v1/user/register \
  -H "Content-Type: application/json" \
  -d '{"email":"buyer@example.com","username":"buyer","first_name":"Иван","last_name":"Иванов","password":"test12345"}'

# 2. Токен подтверждения появится в консоли runserver (EMAIL_BACKEND = console).
# 3. Подтверждение email
curl -X POST http://127.0.0.1:8000/api/v1/user/register/confirm \
  -H "Content-Type: application/json" \
  -d '{"email":"buyer@example.com","token":"<токен>"}'

# 4. Логин — получаем access-токен
curl -X POST http://127.0.0.1:8000/api/v1/user/login \
  -H "Content-Type: application/json" \
  -d '{"email":"buyer@example.com","password":"test12345"}'

# Дальше подставляем access в заголовок Authorization: Bearer <token>
TOKEN="<access>"

# 5. Просмотр каталога
curl "http://127.0.0.1:8000/api/v1/products?category=224"

# 6. Добавление товаров в корзину (от разных магазинов)
curl -X POST http://127.0.0.1:8000/api/v1/basket \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"items":[{"product_info_id":1,"quantity":2},{"product_info_id":15,"quantity":1}]}'

# 7. Создание контакта
curl -X POST http://127.0.0.1:8000/api/v1/contacts \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"city":"Москва","street":"Тверская","house":"1","apartment":"10","phone":"+79001234567"}'

# 8. Подтверждение заказа
curl -X POST http://127.0.0.1:8000/api/v1/order \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"contact":<id_контакта>}'

# 9. Список заказов
curl http://127.0.0.1:8000/api/v1/order -H "Authorization: Bearer $TOKEN"
```

При подтверждении заказа **клиенту** уходит письмо «Заказ №N принят», а **администратору** (`ADMIN_EMAIL` в settings) — накладная со всеми позициями.

---

## Структура проекта

```
retail-procurement-backend/
├── backend/                       # основное приложение
│   ├── management/commands/
│   │   └── import_products.py     # команда импорта YAML
│   ├── migrations/                # миграции БД
│   ├── admin.py                   # регистрация моделей в админке
│   ├── apps.py                    # подключает signals
│   ├── models.py                  # все модели
│   ├── serializers.py             # DRF-сериализаторы
│   ├── signals.py                 # обработчик сигнала сброса пароля
│   ├── urls.py                    # API-маршруты
│   └── views.py                   # API-views
├── config/                        # настройки проекта
│   ├── settings.py
│   └── urls.py
├── orders/                        # пустое, оставлено «на всякий»
├── data/
│   ├── shop1.yaml                 # прайс «Связной»
│   └── shop2.yaml                 # прайс «DNS»
├── .env.example
├── .gitignore
├── manage.py
├── README.md
└── requirements.txt
```

---

## Тесты и ручная проверка

Сквозной сценарий (регистрация → каталог → корзина → контакт → заказ) **проверен вручную** и работает. Все эндпоинты покрыты примерами в разделе «Пример сквозного сценария».
