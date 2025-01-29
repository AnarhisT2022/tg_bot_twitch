# Twitch Telegram Bot

Этот Telegram-бот отправляет уведомления в группу или канал, когда указанный Twitch-канал начинает стрим. Бот использует Twitch API для проверки статуса стрима и библиотеку `python-telegram-bot` для взаимодействия с Telegram.
P.S. Код был создан при помощи ИИ DeepSeek

## 📋 Требования
- Python 3.9 или выше
- Учетная запись на [Twitch Developers](https://dev.twitch.tv/) для получения API-токенов
- Telegram-бот, созданный через [@BotFather](https://t.me/BotFather)

## ⚙️ Установка
1. Клонируйте репозиторий:
```bash
git clone https://github.com/ваш_логин/tg_bot_twitch.git
cd tg_bot_twitch
```

2. Установите зависимости:
```bash
pip install -r requirements.txt
```

3. Создайте файл `.env`:
```env
TELEGRAM_TOKEN=ваш_токен_бота
TELEGRAM_GROUP_CHAT_ID=id_группы
TELEGRAM_ADMIN_CHAT_ID=ваш_личный_chat_id
TWITCH_CHANNEL=логин_стримера
TWITCH_CLIENT_ID=ваш_client_id
TWITCH_CLIENT_SECRET=ваш_client_secret
TWITCH_REFRESH_TOKEN=ваш_refresh_token
```

## 🚀 Запуск
```bash
python tg_bot.py
```

## 🛠 Технологии
- **Python 3.9**
- **python-telegram-bot**
- **Twitch API**