import os
import time
import logging
import sys

import requests

import telegram


from dotenv import load_dotenv
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

TOKEN_ERRORS = ['Отстутствует переменная окружения "TELEGRAM_TOKEN"',
                'Отстутствует переменная окружения "TELEGRAM_CHAT_ID"',
                'Отстутствует переменная окружения "PRACTICUM_TOKEN"']


logging.basicConfig(
    stream=sys.stdout,
    filemode='a',
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.DEBUG)
logging.getLogger(__name__)


def send_message(bot, message):
    """Отправка сообщения"""

    try:
        bot.send_message(TELEGRAM_CHAT_ID, message)
        logging.info('Сообщение успешно отправлено.')
    except Exception as error:
        raise Exception(f'Не удалось отправить сообщение. Код ошибки: {error}')


def get_api_answer(current_timestamp):
    """Отправка запроса к api"""
    timestamp = current_timestamp or int(time.time())
    params = {'from_date': timestamp}

    try:
        homework_statuses = requests.get(
            ENDPOINT, headers=HEADERS, params=params)

        if homework_statuses.status_code != 200:
            raise Exception('Не верный status code запроса')
        return homework_statuses.json()

    except Exception as error:
        logging.error(error)
        raise Exception('Что пошло не так при получении ответа от сервера')


def check_response(response):
    """Проверка коректности ответа сервера"""

    if isinstance(response, dict):
        if 'homeworks' not in response:
            raise KeyError('В ответе отсутствует homeworks')

    if not isinstance(response['homeworks'], list):
        raise TypeError('Ответ не представлен в виде списка')
    return response['homeworks']


def parse_status(homework):
    """Получение статуса домашки """
    homework_name = homework['homework_name']
    homework_status = homework['status']

    if homework_status not in HOMEWORK_STATUSES:
        raise ValueError(f'Неизвестный статус {homework_status}')

    return (f'Изменился статус проверки работы'
            f'"{homework_name}". {HOMEWORK_STATUSES[homework_status]}')


def check_tokens():
    """Проверка наличия переменных окружения"""

    tokens = [
        [TELEGRAM_TOKEN, None, TOKEN_ERRORS[0]],
        [TELEGRAM_CHAT_ID, None, TOKEN_ERRORS[1]],
        [PRACTICUM_TOKEN, None, TOKEN_ERRORS[2]]
    ]
    for token, value, error in tokens:
        if token is value:
            logging.critical(error)
            return False
    return True


def main():
    """Основная логика работы бота."""

    try:
        check_tokens()
    except Exception as error:
        logging.critical(f'Не хватает переменной окружения! {error}')

    bot = telegram.Bot(token=TELEGRAM_TOKEN)
    current_timestamp = int(time.time())

    while True:
        try:
            response = get_api_answer(current_timestamp)
            print(response)
            message = parse_status(check_response(response))
            send_message(bot, message)
            current_timestamp = response.get(
                'current_date',
                current_timestamp
            )
            time.sleep(RETRY_TIME)
        except Exception as error:
            message = f'Сбой в работе программы: {error}'
            current_error = message
            logging.error(message, exc_info=True)
            if current_error != message:
                send_message(bot, message)
            time.sleep(30)


if __name__ == '__main__':
    main()
