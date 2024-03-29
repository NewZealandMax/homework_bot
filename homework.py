import json
import logging
import os
import sys
import time
from http import HTTPStatus

import requests
import telegram
from dotenv import load_dotenv

import exceptions


load_dotenv()


PRACTICUM_TOKEN = os.getenv('PRACTICUM_TOKEN')
TELEGRAM_TOKEN = os.getenv('TELEGRAM_TOKEN')
TELEGRAM_CHAT_ID = os.getenv('TELEGRAM_CHAT_ID')


RETRY_TIME = 600
ENDPOINT = 'https://practicum.yandex.ru/api/user_api/homework_statuses/'
HEADERS = {'Authorization': f'OAuth {PRACTICUM_TOKEN}'}


HOMEWORK_STATUSES = {
    'approved': 'Работа проверена: ревьюеру всё понравилось. Ура!',
    'reviewing': 'Работа взята на проверку ревьюером.',
    'rejected': 'Работа проверена: у ревьюера есть замечания.'
}


logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)
handler = logging.StreamHandler(stream=sys.stdout)
formatter = logging.Formatter(
    '%(asctime)s %(levelname)s %(message)s %(name)s'
)
handler.setFormatter(formatter)
logger.addHandler(handler)


def send_message(bot, message):
    """Отправлет сообщение в Telegram чат."""
    try:
        bot.send_message(TELEGRAM_CHAT_ID, message)
        logger.info('Сообщение успешно отправлено.')
    except telegram.TelegramError as error:
        logger.error(error, exc_info=True)


def get_api_answer(current_timestamp):
    """Делает запрос к API, возвращает данные Python."""
    timestamp = current_timestamp or int(time.time())
    params = {'from_date': timestamp}
    try:
        response = requests.get(ENDPOINT, headers=HEADERS, params=params)
    except requests.ConnectionError as error:
        logger.error(error, exc_info=True)
        raise error
    if not response.status_code == HTTPStatus.OK:
        raise exceptions.Response200Error('Запрос не вернул код 200.')
    try:
        response = response.json()
    except json.JSONDecodeError as error:
        logger.error(error, exc_info=True)
        raise error
    return response


def check_response(response):
    """
    Проверяет ответ API на корректность.
    Если верно, возвращает список домашних работ.
    """
    key = 'homeworks'
    if not isinstance(response, dict):
        raise exceptions.NotDictError('Ответ API не является словарём.')
    if key not in response:
        raise KeyError(f'Ключ "{key}" не найден.')
    homeworks = response.get(key)
    if not isinstance(homeworks, list):
        raise exceptions.NotListError(
            f'Значение ключа "{key}" не является списком.'
        )
    return homeworks


def parse_status(homework):
    """Извлекает статус домашней работы, в случае успеха возвращает вердикт."""
    keys = [
        'homework_name',
        'status',
    ]
    for key in keys:
        if key not in homework:
            raise KeyError(f'Ключ "{key}" не найден в ответе API.')
    homework_name = homework.get('homework_name')
    homework_status = homework.get('status')
    if homework_status not in HOMEWORK_STATUSES:
        raise KeyError(
            (f'Неизвестный статус "{homework_status}" '
             f'в работе "{homework_name}"')
        )
    verdict = HOMEWORK_STATUSES.get(homework_status)
    return f'Изменился статус проверки работы "{homework_name}". {verdict}'


def check_tokens():
    """Проверяет доступность переменных окружения, возвращает bool."""
    return bool(PRACTICUM_TOKEN and TELEGRAM_TOKEN and TELEGRAM_CHAT_ID)


def token_empty_error():
    """Логирует ошибку токена, выбрасывает исключение."""
    tokens = {
        PRACTICUM_TOKEN: 'PRACTICUM_TOKEN',
        TELEGRAM_TOKEN: 'TELEGRAM_TOKEN',
        TELEGRAM_CHAT_ID: 'TELEGRAM_CHAT_ID',
    }
    for token in tokens:
        if not token:
            error = ('Отсутствует обязательная переменная '
                     f'окружения "{token}". '
                     'Программа принудительно остановлена.')
        logger.critical(error, exc_info=True)
        raise exceptions.TokenError(error)


def main():
    """Основная логика работы бота."""
    if not check_tokens():
        token_empty_error()
    bot = telegram.Bot(token=TELEGRAM_TOKEN)
    current_timestamp = int(time.time())
    message_status = ''
    while True:
        try:
            response = get_api_answer(current_timestamp)
            homeworks = check_response(response)
            current_timestamp = int(time.time())
        except Exception as error:
            message = f'Сбой в работе программы: {error}'
            logger.error(message, exc_info=True)
            if not message == message_status:
                send_message(bot, message)
                message_status = message
            time.sleep(RETRY_TIME)
        else:
            if homeworks:
                for homework in homeworks:
                    try:
                        message = parse_status(homework)
                    except KeyError as error:
                        message = f'Сбой в работе программы: {error}'
                        logger.error(message, exc_info=True)
                    send_message(bot, message)
            else:
                logger.debug('Обновлений нет')
            time.sleep(RETRY_TIME)


if __name__ == '__main__':
    main()
