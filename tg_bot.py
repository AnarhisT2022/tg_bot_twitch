import os
import requests
import asyncio
import time
from dotenv import load_dotenv
from telegram import Bot
from telegram.error import TelegramError

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
            self.token_expires_at = time.time() + data['expires_in'] - 60  # Запас 60 секунд: E501

            # Обновляем .env файл с новым refresh token
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
        with open('.env', 'r') as f:
            lines = f.readlines()

        with open('.env', 'w') as f:
            for line in lines:
                if line.startswith('TWITCH_REFRESH_TOKEN='):
                    f.write(f'TWITCH_REFRESH_TOKEN={new_refresh_token}\n')
                else:
                    f.write(line)


# Инициализация менеджера токенов
token_manager = TwitchTokenManager()

# Конфигурация Telegram
TELEGRAM_TOKEN = os.getenv('TELEGRAM_TOKEN')
TELEGRAM_GROUP_CHAT_ID = os.getenv('TELEGRAM_GROUP_CHAT_ID')
TELEGRAM_ADMIN_CHAT_ID = os.getenv('TELEGRAM_ADMIN_CHAT_ID')
TWITCH_CHANNEL = os.getenv('TWITCH_CHANNEL')

# Инициализация бота Telegram
bot = Bot(token=TELEGRAM_TOKEN)

# Переменная для отслеживания состояния стрима
stream_is_live = False


async def check_twitch_stream():
    global stream_is_live

    try:
        # Получаем актуальный Access Token
        access_token = await token_manager.get_access_token()
        if not access_token:
            await send_telegram_message(
                TELEGRAM_ADMIN_CHAT_ID,
                "❌ Ошибка: Не удалось получить Twitch токен"
                )
            return

        # Запрос к Twitch API
        url = "https://api.twitch.tv/helix/streams"
        headers = {
            "Client-ID": token_manager.client_id,
            "Authorization": f"Bearer {access_token}"
        }
        params = {"user_login": TWITCH_CHANNEL}

        response = requests.get(url, headers=headers, params=params)
        response.raise_for_status()
        data = response.json()

        if data['data']:  # Стрим активен
            if not stream_is_live:  # Если стрим только что начался
                stream_data = data['data'][0]
                message = (
                    f"🎮 <b>{TWITCH_CHANNEL}</b> начал стрим!\n"
                    f"📺 <b>Название:</b> <i>{stream_data['title']}</i>\n"
                    f"🕹 <b>Категория:</b> <i>{stream_data['game_name']}</i>\n"
                    f"🔗 <b>Ссылка:</b> https://twitch.tv/{TWITCH_CHANNEL}\n"
                    f"<u>Уведомление было создано автоматически ботом</u>"
                )

                await send_telegram_message(TELEGRAM_GROUP_CHAT_ID, message)
                print("Уведомление отправлено!")
                stream_is_live = True  # Обновляем состояние
        else:  # Стрим не активен*
            if stream_is_live:  # Если стрим только что закончился
                print("Стрим завершен")
                stream_is_live = False  # Обновляем состояние

    except Exception as e:
        print(f"Ошибка при проверке стрима: {e}")
        await send_telegram_message(
            TELEGRAM_ADMIN_CHAT_ID,
            f"⚠️ Ошибка проверки стрима: {str(e)}"
            )


async def send_telegram_message(chat_id, message):
    try:
        await bot.send_message(
            chat_id=chat_id,
            text=message,
            parse_mode='HTML',
            disable_web_page_preview=False
        )
    except TelegramError as e:
        print(f"Ошибка отправки сообщения: {e}")


async def main():
    while True:
        await check_twitch_stream()
        await asyncio.sleep(300)  # Проверка каждые 300 секунд

if __name__ == "__main__":
    asyncio.run(main())
