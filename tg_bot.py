import os
import requests
import asyncio
import time
from dotenv import load_dotenv
from telegram import Bot
from telegram.error import TelegramError
from telegram.request import HTTPXRequest

# Загружаем переменные окружения
load_dotenv()


class TwitchTokenManager:
    def __init__(self):
        self.client_id = os.getenv('TWITCH_CLIENT_ID')
        self.client_secret = os.getenv('TWITCH_CLIENT_SECRET')
        self.refresh_token = os.getenv('TWITCH_REFRESH_TOKEN')
        self.access_token = None
        self.token_expires_at = 0

    async def get_access_token(self):
        if self.access_token and time.time() < self.token_expires_at:
            return self.access_token

        # Обновляем токен
        url = "https://id.twitch.tv/oauth2/token"
        params = {
            "client_id": self.client_id,
            "client_secret": self.client_secret,
            "grant_type": "refresh_token",
            "refresh_token": self.refresh_token
        }

        try:
            response = requests.post(url, params=params)
            response.raise_for_status()
            data = response.json()

            self.access_token = data['access_token']
            self.refresh_token = data.get('refresh_token', self.refresh_token)
            self.token_expires_at = time.time() + data['expires_in'] - 60

            if 'refresh_token' in data:
                self._update_env_file(data['refresh_token'])

            return self.access_token
        except Exception as e:
            print(f"Ошибка обновления токена: {e}")
            await send_telegram_message(
                os.getenv('TELEGRAM_ADMIN_CHAT_ID'),
                f"❌ Ошибка обновления токена: {e}"
            )
            return None

    def _update_env_file(self, new_refresh_token):
        env_path = '.env'
        if not os.path.exists(env_path):
            print(f"Файл {env_path} не найден")
            return

        with open(env_path, 'r') as f:
            lines = f.readlines()

        with open(env_path, 'w') as f:
            updated = False
            for line in lines:
                if line.startswith('TWITCH_REFRESH_TOKEN='):
                    f.write(f'TWITCH_REFRESH_TOKEN={new_refresh_token}\n')
                    updated = True
                else:
                    f.write(line)
            if not updated:
                f.write(f'\nTWITCH_REFRESH_TOKEN={new_refresh_token}')


# Инициализация бота Telegram с обработкой прокси
async def create_bot():
    TELEGRAM_TOKEN = os.getenv('TELEGRAM_TOKEN')
    PROXY_URL = os.getenv('PROXY_URL')

    if PROXY_URL:
        print(f"Используется прокси: {PROXY_URL}")
        request = HTTPXRequest(
            proxy_url=PROXY_URL,
            connect_timeout=30.0,
            read_timeout=30.0,
            write_timeout=30.0
        )
        return Bot(token=TELEGRAM_TOKEN, request=request)
    else:
        request = HTTPXRequest(
            connect_timeout=30.0,
            read_timeout=30.0,
            write_timeout=30.0
        )
        return Bot(token=TELEGRAM_TOKEN, request=request)


# Инициализация
token_manager = TwitchTokenManager()

# Конфигурация
TELEGRAM_GROUP_CHAT_ID = os.getenv('TELEGRAM_GROUP_CHAT_ID')
TELEGRAM_ADMIN_CHAT_ID = os.getenv('TELEGRAM_ADMIN_CHAT_ID')
TWITCH_CHANNEL = os.getenv('TWITCH_CHANNEL')

# Переменная для отслеживания состояния стрима
stream_is_live = False


async def send_telegram_message(chat_id, message, max_retries=3):
    bot = await create_bot()

    for attempt in range(max_retries):
        try:
            await bot.send_message(
                chat_id=chat_id,
                text=message,
                parse_mode='HTML',
                disable_web_page_preview=True
            )
            print(f"Сообщение успешно отправлено в чат {chat_id}")
            return True
        except TelegramError as e:
            print(f"Попытка {attempt + 1}/{max_retries}: "
                  f"Ошибка отправки сообщения: {e}")
            if attempt < max_retries - 1:
                await asyncio.sleep(2 ** attempt)  # Экспоненциальная задержка
            else:
                print(f"Не удалось отправить сообщение после"
                      f"{max_retries} попыток")
                return False
        except Exception as e:
            print(f"Неожиданная ошибка: {e}")
            return False


async def check_twitch_stream():
    global stream_is_live

    try:
        # Получаем актуальный Access Token
        access_token = await token_manager.get_access_token()
        if not access_token:
            print("Не удалось получить Twitch токен")
            return

        # Запрос к Twitch API
        url = "https://api.twitch.tv/helix/streams"
        headers = {
            "Client-ID": token_manager.client_id,
            "Authorization": f"Bearer {access_token}"
        }
        params = {"user_login": TWITCH_CHANNEL}

        response = requests.get(url,
                                headers=headers,
                                params=params,
                                timeout=10)
        response.raise_for_status()
        data = response.json()

        if data['data']:  # Стрим активен
            if not stream_is_live:
                stream_data = data['data'][0]
                message = (
                    f"🎮 <b>{TWITCH_CHANNEL}</b> начал стрим!\n"
                    f"📺 <b>Название:</b> <i>{stream_data['title']}</i>\n"
                    f"🕹 <b>Категория:</b> <i>{stream_data['game_name']}</i>\n"
                    f"🔗 <b>Ссылка:</b> https://twitch.tv/{TWITCH_CHANNEL}\n"
                    f"<u>Уведомление было создано автоматически ботом</u>"
                )

                success = await send_telegram_message(TELEGRAM_GROUP_CHAT_ID,
                                                      message)
                if success:
                    print("Уведомление отправлено!")
                stream_is_live = True
        else:
            if stream_is_live:
                print("Стрим завершен")
                stream_is_live = False

    except requests.exceptions.Timeout:
        print("Таймаут при запросе к Twitch API")
    except requests.exceptions.RequestException as e:
        print(f"Ошибка сети при запросе к Twitch API: {e}")
    except Exception as e:
        print(f"Ошибка при проверке стрима: {e}")
        await send_telegram_message(
            TELEGRAM_ADMIN_CHAT_ID,
            f"⚠️ Ошибка проверки стрима: {str(e)}"
        )


async def main():
    # Тестовое сообщение при старте
    await send_telegram_message(
        TELEGRAM_ADMIN_CHAT_ID,
        f"🤖 Бот запущен. Отслеживание канала: {TWITCH_CHANNEL}"
    )

    while True:
        await check_twitch_stream()
        print(f"Проверка завершена. Следующая проверка через 5 минут. "
              f"Статус стрима: {'включен' if stream_is_live else 'выключен'}")
        await asyncio.sleep(300)


if __name__ == "__main__":
    asyncio.run(main())
