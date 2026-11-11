# Дашборд в Apache Superset

В дашборде четыре блока: конверсия в покупку, выручка на клиента, доля посетивших сайт и таблица метрик. Фильтр `Purchase channel` позволяет смотреть исходный канал покупок клиента. Срезы используются для исследования, а не для подтверждения новых гипотез.

## Запуск

Нужен Docker Desktop. Сначала из корня проекта пересчитать анализ:

```bash
python run_analysis.py
python bi/configure.py
docker compose --env-file bi/.env -f bi/compose.yml up -d
docker compose --env-file bi/.env -f bi/compose.yml logs -f superset
```

При первом запуске загружается официальный образ `apache/superset:6.0.0`, затем создаются локальный пользователь, подключение к данным, графики и дашборд. Дождаться строки `Dashboard ready` и запуска сервера.

Адрес: [localhost:8088](http://localhost:8088/superset/dashboard/hillstrom-email-experiment/).

Логин: `student`. Случайный пароль сохранён в `bi/.env`, который исключён из Git. Повторный запуск `configure.py` сохраняет существующие настройки.

Для остановки:

```bash
docker compose --env-file bi/.env -f bi/compose.yml down
```

Контейнер доступен только через localhost. Это локальное учебное окружение с SQLite, не конфигурация для публичного сервера. Основные расчёты и интервалы находятся в Python и Excel; фильтрация BI-графиков не пересчитывает статистические тесты.

Документация: [Superset Quickstart](https://superset.apache.org/user-docs/quickstart/).
