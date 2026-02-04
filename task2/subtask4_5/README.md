# Задание 2. Архитектура системы отчетов BionicPRO

## Задача 4/Задача 5

Реализация безопасного доступа к отчётам с использованием Keycloak и PKCE.

## Архитектура безопасности

### Ограничение доступа к эндпоинтам

1. **`/reports/me`** - защищённый эндпоинт, возвращает отчёт только для текущего аутентифицированного пользователя

   - Использует `client_id` из JWT токена для определения пользователя
   - Пользователь может получить только свои данные

2. **`/reports/client/{client_id}/secure`** - защищённый эндпоинт с проверкой прав

   - Обычный пользователь может получить только свой отчёт (`client_id` в токене должен совпадать)св
   - Администратор (`admin` role) может получить отчёт любого пользователя

3. **`/reports/clients`**, **`/reports/client/{client_id}`**, **`/reports/prosthesis/{serial_number}`** - публичные эндпоинты

## Компоненты

### API

- JWT валидация через Keycloak JWKS
- Извлечение `client_id` из JWT токена
- Проверка ролей для разграничения доступа

### Frontend (React/Keycloak-js)

- Аутентификация через Keycloak с PKCE
- Кнопка генерации отчёта
- Отображение данных клиента и телеметрии

### Keycloak

- Realm: `reports-realm`
- Клиенты:
  - `reports-frontend` - публичный клиент для SPA
  - `reports-api` - bearer-only клиент для API
- Пользователи:
  - `user1` / `password` (client_id: 1)
  - `user2` / `password` (client_id: 2)
  - `admin` / `admin` (администратор)

## Запуск

```bash
cd task2/subtask4_5
docker-compose up --build -d
```

## Сервисы

| Сервис   | URL                   | Описание                 |
| -------- | --------------------- | ------------------------ |
| Frontend | http://localhost:3000 | Web-интерфейс отчётов    |
| API      | http://localhost:8000 | Reports API              |
| Keycloak | http://localhost:8180 | Keycloak сервер          |
| Airflow  | http://localhost:8080 | Airflow UI (admin/admin) |

## Проверка работы

1. Откройте http://localhost:3000
2. Нажмите **Sign In**
3. Войдите как `user1` / `password`
4. Выберите период и нажмите **Generate Report**
5. Убедитесь, что отображаются данные только для client_id=1
